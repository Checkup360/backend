import uuid
from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select, update

from app.domain.services.form_registry import FormRegistry
from app.domain.value_objects.org_role import OrgRole
from app.infrastructure.persistence.models import (
    AssessmentSubmissionModel,
    MemberDetails,
    MemberHealthData,
    MemberOverallScoreModel,
    Membership,
    Organization,
    OrganizationScoreWeightsModel,
)

ORG_SLUG = "employee-directory-org"


async def _organization(db_session_maker) -> Organization:
    async with db_session_maker() as session:
        organization = await session.scalar(
            select(Organization).where(Organization.slug == ORG_SLUG)
        )
        assert organization is not None
        return organization


async def _add_member(
    make_user, make_membership, db_session_maker, organization, *, email, name=None
):
    user = await make_user(email=email)
    await make_membership(
        user_id=user.id, organization_id=organization.id, role="member"
    )
    if name is not None:
        first_name, last_name = name
        async with db_session_maker() as session:
            session.add(
                MemberDetails(
                    user_id=user.id,
                    date_of_birth=date(1990, 1, 1),
                    first_name=first_name,
                    last_name=last_name,
                )
            )
            await session.commit()
    return user


async def _complete_every_form(db_session_maker, organization, user) -> None:
    async with db_session_maker() as session:
        for form_type in FormRegistry().get_registered_form_types():
            session.add(
                AssessmentSubmissionModel(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    organization_id=organization.id,
                    form_type=form_type,
                    form_version="1",
                    status="completed",
                    submitted_at=datetime.now(timezone.utc),
                )
            )
        await session.commit()


async def _score(db_session_maker, organization, user) -> None:
    async with db_session_maker() as session:
        weights = OrganizationScoreWeightsModel(
            organization_id=organization.id,
            version=1,
            weights={"diabetes": 100.0},
        )
        session.add(weights)
        await session.flush()
        session.add(
            MemberOverallScoreModel(
                user_id=user.id,
                organization_id=organization.id,
                score_weights_id=weights.id,
                overall_health_index=72.5,
                risk_level="low",
                evaluated_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
            )
        )
        await session.commit()


@pytest_asyncio.fixture
async def directory(
    client, db_session_maker, auth_scenario, make_user, make_membership
):
    await auth_scenario.register_and_login(
        email="directory-admin@example.com",
        memberships=[(ORG_SLUG, OrgRole.ADMIN)],
    )
    organization = await _organization(db_session_maker)
    add = lambda **kwargs: _add_member(  # noqa: E731
        make_user, make_membership, db_session_maker, organization, **kwargs
    )

    up_to_date = await add(email="a-up@example.com", name=("Matías", "Pérez"))
    pending = await add(email="b-pending@example.com", name=("Ana", "Gómez"))
    onboarding = await add(email="c-onboarding@example.com")
    inactive = await add(email="d-inactive@example.com", name=("Luis", "Díaz"))

    await _complete_every_form(db_session_maker, organization, up_to_date)
    await _score(db_session_maker, organization, up_to_date)
    async with db_session_maker() as session:
        await session.execute(
            update(Membership).where(Membership.user_id == inactive.id).values(roles=[])
        )
        await session.commit()
    return organization, {
        "up_to_date": up_to_date,
        "pending": pending,
        "onboarding": onboarding,
        "inactive": inactive,
    }


def _by_email(response) -> dict[str, dict]:
    assert response.status_code == 200
    return {employee["email"]: employee for employee in response.json()}


class TestEmployeeDirectoryQuery:
    @pytest.mark.asyncio
    async def test_status_is_derived_for_each_kind_of_employee(self, client, directory):
        organization, _ = directory

        employees = _by_email(
            client.get(f"/organizations/{organization.id}/employees?role=member")
        )
        statuses = {email: e["status"] for email, e in employees.items()}

        assert statuses["a-up@example.com"] == "up_to_date"
        assert statuses["b-pending@example.com"] == "pending_assessments"
        assert statuses["c-onboarding@example.com"] == "onboarding"

        inactive = _by_email(
            client.get(
                f"/organizations/{organization.id}/employees?membership=inactive"
            )
        )
        assert inactive["d-inactive@example.com"]["status"] == "inactive"

    @pytest.mark.asyncio
    async def test_status_filter_narrows_rows_and_total(self, client, directory):
        organization, _ = directory

        response = client.get(
            f"/organizations/{organization.id}/employees"
            "?status=pending_assessments&page=1&page_size=10"
        )

        assert [e["email"] for e in response.json()] == ["b-pending@example.com"]
        assert response.headers["X-Total-Count"] == "1"

    @pytest.mark.asyncio
    async def test_pagination_returns_pages_in_email_order_with_full_total(
        self, client, directory
    ):
        organization, _ = directory
        url = f"/organizations/{organization.id}/employees?role=member&page_size=2"

        first = client.get(url + "&page=1")
        second = client.get(url + "&page=2")

        assert [e["email"] for e in first.json()] == [
            "a-up@example.com",
            "b-pending@example.com",
        ]
        assert [e["email"] for e in second.json()] == ["c-onboarding@example.com"]
        assert first.headers["X-Total-Count"] == "3"
        assert second.headers["X-Page"] == "2"

    @pytest.mark.asyncio
    async def test_score_filter_separates_scored_from_unscored(self, client, directory):
        organization, _ = directory
        base = f"/organizations/{organization.id}/employees?role=member"

        scored = _by_email(client.get(base + "&score=scored"))
        unscored = _by_email(client.get(base + "&score=unscored"))

        assert set(scored) == {"a-up@example.com"}
        assert scored["a-up@example.com"]["overall_health_index"] == 72.5
        assert scored["a-up@example.com"]["last_assessment"] is not None
        assert set(unscored) == {"b-pending@example.com", "c-onboarding@example.com"}

    @pytest.mark.asyncio
    async def test_sorting_by_score_orders_across_pages_with_unscored_last(
        self, client, directory
    ):
        organization, _ = directory
        base = (
            f"/organizations/{organization.id}/employees"
            "?role=member&sort_by=score&page_size=2"
        )

        descending = client.get(base + "&sort_direction=desc&page=1")
        ascending = client.get(base + "&sort_direction=asc&page=1")

        assert descending.json()[0]["email"] == "a-up@example.com"
        assert ascending.json()[0]["email"] == "a-up@example.com"
        assert descending.headers["X-Total-Count"] == "3"

    @pytest.mark.asyncio
    async def test_sorting_by_name_respects_direction(self, client, directory):
        organization, _ = directory
        base = f"/organizations/{organization.id}/employees?role=member&sort_by=name"

        ascending = client.get(base + "&sort_direction=asc")
        descending = client.get(base + "&sort_direction=desc")

        assert [e["email"] for e in ascending.json()] == [
            "b-pending@example.com",
            "c-onboarding@example.com",
            "a-up@example.com",
        ]
        assert [e["email"] for e in descending.json()] == [
            "a-up@example.com",
            "c-onboarding@example.com",
            "b-pending@example.com",
        ]

    @pytest.mark.asyncio
    async def test_search_ignores_accents_and_treats_wildcards_literally(
        self, client, directory
    ):
        organization, _ = directory
        base = f"/organizations/{organization.id}/employees"

        by_name = _by_email(client.get(base + "?search=matias perez"))
        by_accented_name = _by_email(client.get(base + "?search=Gómez"))
        wildcard = client.get(base + "?search=%25")

        assert set(by_name) == {"a-up@example.com"}
        assert set(by_accented_name) == {"b-pending@example.com"}
        assert wildcard.json() == []

    @pytest.mark.asyncio
    async def test_form_completed_through_health_data_counts_as_up_to_date(
        self, client, db_session_maker, directory
    ):
        organization, users = directory
        async with db_session_maker() as session:
            await session.execute(
                update(OrganizationScoreWeightsModel)
                .where(OrganizationScoreWeightsModel.organization_id == organization.id)
                .values(weights={"diabetes": 0.0})
            )
            session.add(MemberHealthData(user_id=users["pending"].id, height=170.0))
            await session.commit()

        employees = _by_email(
            client.get(f"/organizations/{organization.id}/employees?role=member")
        )

        assert employees["b-pending@example.com"]["status"] == "up_to_date"
        assert employees["c-onboarding@example.com"]["status"] == "onboarding"
