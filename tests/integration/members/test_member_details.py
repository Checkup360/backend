from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.domain.value_objects.org_role import OrgRole
from app.infrastructure.persistence.models import MemberDetails


class TestMemberDetailsOnboarding:
    @pytest.mark.asyncio
    async def test_member_without_details_requires_onboarding(
        self, client, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="member-onboarding-required@example.com",
            memberships=[("member-onboarding-required", OrgRole.MEMBER)],
        )

        response = client.get("/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["requires_onboarding"] is True
        assert "date_of_birth" not in data

    @pytest.mark.asyncio
    async def test_submit_details_completes_onboarding(
        self, client, auth_scenario, db_session_maker
    ):
        user = await auth_scenario.register_and_login(
            email="member-onboarding-complete@example.com",
            memberships=[("member-onboarding-complete", OrgRole.MEMBER)],
        )

        response = client.post(
            "/members/me/details",
            json={"date_of_birth": "1990-06-15"},
        )

        assert response.status_code == 200
        assert response.json() == {"ok": True}

        async with db_session_maker() as session:
            details = await session.scalar(
                select(MemberDetails).where(MemberDetails.user_id == user.id)
            )

        assert details is not None
        assert details.date_of_birth == date(1990, 6, 15)

        me_response = client.get("/auth/me")
        assert me_response.status_code == 200
        data = me_response.json()
        assert data["requires_onboarding"] is False
        assert "date_of_birth" not in data

    @pytest.mark.asyncio
    async def test_future_date_is_rejected_without_creating_details(
        self, client, auth_scenario, db_session_maker
    ):
        user = await auth_scenario.register_and_login(
            email="member-onboarding-future@example.com",
            memberships=[("member-onboarding-future", OrgRole.MEMBER)],
        )
        future_date = date.today() + timedelta(days=1)

        response = client.post(
            "/members/me/details",
            json={"date_of_birth": future_date.isoformat()},
        )

        assert response.status_code == 422
        async with db_session_maker() as session:
            details = await session.scalar(
                select(MemberDetails).where(MemberDetails.user_id == user.id)
            )

        assert details is None

    @pytest.mark.asyncio
    async def test_org_admin_and_sysadmin_do_not_require_onboarding(
        self, client, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="admin-no-onboarding@example.com",
            memberships=[("admin-no-onboarding", OrgRole.ADMIN)],
        )

        admin_response = client.get("/auth/me")
        assert admin_response.status_code == 200
        assert admin_response.json()["requires_onboarding"] is False

        client.cookies.clear()
        await auth_scenario.register_and_login(
            email="sysadmin-no-onboarding@example.com",
            is_superuser=True,
        )

        sysadmin_response = client.get("/auth/me")
        assert sysadmin_response.status_code == 200
        assert sysadmin_response.json()["requires_onboarding"] is False
