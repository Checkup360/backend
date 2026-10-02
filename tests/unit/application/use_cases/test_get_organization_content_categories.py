import uuid
from unittest.mock import AsyncMock

import pytest

from app.application.dto.risk_scoring import ScoreCatalogItemDTO
from app.application.use_cases.organizations.get_organization_content_categories import (
    GetOrganizationContentCategoriesUseCase,
)
from app.domain.entities.membership import Membership
from app.domain.entities.organization import Organization
from app.domain.exceptions import NotOrganizationAdminError, OrganizationNotFoundError
from app.domain.value_objects import OrgRole

ORG_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


def _use_case(roles: list[OrgRole] | None, organization: Organization | None):
    membership_repo = AsyncMock()
    membership_repo.get_by_user_and_org.return_value = (
        Membership(user_id=USER_ID, organization_id=ORG_ID, roles=roles)
        if roles is not None
        else None
    )
    org_repo = AsyncMock()
    org_repo.get.return_value = organization
    scoring_service = AsyncMock()
    scoring_service.get_catalog.return_value = [
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
    return GetOrganizationContentCategoriesUseCase(
        membership_repo, org_repo, scoring_service
    )


def _organization(score_weights: dict[str, float]) -> Organization:
    return Organization(
        id=ORG_ID, name="Acme", slug="acme", score_weights=score_weights
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role", [OrgRole.CONTENT_MANAGER, OrgRole.ADMIN, OrgRole.SUPERADMIN]
)
async def test_lists_catalog_topics_flagging_active_ones(role: OrgRole):
    use_case = _use_case([role], _organization({"diabetes": 0.0, "audit_c": 20.0}))

    categories = await use_case.execute(USER_ID, False, ORG_ID)

    assert [(c.key, c.label, c.active) for c in categories] == [
        ("diabetes", "Diabetes", False),
        ("audit_c", "Alcohol Risk Assessment", True),
    ]


@pytest.mark.asyncio
async def test_rejects_members_without_content_role():
    use_case = _use_case([OrgRole.MEMBER], _organization({"diabetes": 10.0}))

    with pytest.raises(NotOrganizationAdminError):
        await use_case.execute(USER_ID, False, ORG_ID)


@pytest.mark.asyncio
async def test_rejects_users_outside_the_organization():
    use_case = _use_case(None, _organization({"diabetes": 10.0}))

    with pytest.raises(NotOrganizationAdminError):
        await use_case.execute(USER_ID, False, ORG_ID)


@pytest.mark.asyncio
async def test_superuser_does_not_need_membership():
    use_case = _use_case(None, _organization({"diabetes": 10.0}))

    categories = await use_case.execute(USER_ID, True, ORG_ID)

    assert [c.key for c in categories if c.active] == ["diabetes"]


@pytest.mark.asyncio
async def test_unknown_organization_is_rejected():
    use_case = _use_case([OrgRole.ADMIN], None)

    with pytest.raises(OrganizationNotFoundError):
        await use_case.execute(USER_ID, False, ORG_ID)
