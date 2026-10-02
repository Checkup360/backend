from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.application.dto.risk_scoring import ScoreCatalogItemDTO
from app.domain.value_objects.org_role import OrgRole
from app.infrastructure.persistence.models import Organization
from app.presentation.api.dependencies import get_risk_scoring_service
from app.presentation.main import app


async def _organization_id(db_session_maker, slug: str, score_weights=None):
    async with db_session_maker() as session:
        organization = await session.scalar(
            select(Organization).where(Organization.slug == slug)
        )
        assert organization is not None
        if score_weights is not None:
            organization.score_weights = score_weights
            await session.commit()
        return organization.id


class TestOrganizationContentCategories:
    @pytest.fixture(autouse=True)
    def scoring_catalog(self):
        service = AsyncMock()
        service.get_catalog.return_value = [
            ScoreCatalogItemDTO(
                score_id="findrisc",
                score_name="FINDRISC",
                domain="Diabetes",
                topic_key="diabetes",
                topic_label="Diabetes",
            ),
            ScoreCatalogItemDTO(
                score_id="audit_c",
                score_name="AUDIT-C Alcohol Risk",
                domain="Alcohol Use",
                topic_key="audit_c",
                topic_label="Alcohol Risk Assessment",
            ),
        ]
        app.dependency_overrides[get_risk_scoring_service] = lambda: service
        yield service
        app.dependency_overrides.pop(get_risk_scoring_service, None)

    @pytest.mark.asyncio
    async def test_content_manager_lists_categories_with_active_flag(
        self, client, db_session_maker, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="content-manager@example.com",
            memberships=[("content-org", OrgRole.CONTENT_MANAGER)],
        )
        org_id = await _organization_id(
            db_session_maker, "content-org", {"diabetes": 0.0, "audit_c": 40.0}
        )

        res = client.get(f"/organizations/{org_id}/content-categories")

        assert res.status_code == 200
        assert res.json() == [
            {"key": "diabetes", "label": "Diabetes", "active": False},
            {"key": "audit_c", "label": "Alcohol Risk Assessment", "active": True},
        ]

    @pytest.mark.asyncio
    async def test_regular_member_is_forbidden(
        self, client, db_session_maker, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="content-plain-member@example.com",
            memberships=[("content-member-org", OrgRole.MEMBER)],
        )
        org_id = await _organization_id(db_session_maker, "content-member-org")

        res = client.get(f"/organizations/{org_id}/content-categories")

        assert res.status_code == 403
