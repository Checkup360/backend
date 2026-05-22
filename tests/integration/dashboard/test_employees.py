import pytest
from sqlalchemy import select

from app.domain.entities.org_role import OrgRole
from app.persistence.models import Organization


async def _get_organization_by_slug(db_session_maker, slug: str) -> Organization:
    async with db_session_maker() as session:
        organization = await session.scalar(
            select(Organization).where(Organization.slug == slug)
        )
        assert organization is not None
        return organization


class TestDashboardEmployees:
    @pytest.mark.asyncio
    async def test_org_admin_can_list_real_members(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="dashboard-admin@example.com",
            memberships=[("dashboard-org", OrgRole.ADMIN)],
        )
        organization = await _get_organization_by_slug(
            db_session_maker, "dashboard-org"
        )
        member_a = await make_user(email="ana.employee@example.com")
        member_b = await make_user(email="zoe.employee@example.com")
        await make_membership(
            user_id=member_a.id,
            organization_id=organization.id,
            role="member",
        )
        await make_membership(
            user_id=member_b.id,
            organization_id=organization.id,
            role="member",
        )

        response = client.get("/dashboard/employees")

        assert response.status_code == 200
        data = response.json()
        assert [employee["email"] for employee in data] == [
            "ana.employee@example.com",
            "zoe.employee@example.com",
        ]
        assert all(employee["role"] == "member" for employee in data)
        assert all("risk" not in employee for employee in data)

    @pytest.mark.asyncio
    async def test_org_admin_only_sees_members_from_their_organization(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_organization,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="dashboard-admin-own-org@example.com",
            memberships=[("own-dashboard-org", OrgRole.ADMIN)],
        )
        own_organization = await _get_organization_by_slug(
            db_session_maker, "own-dashboard-org"
        )
        other_organization = await make_organization(
            name="Other Dashboard Org", slug="other-dashboard-org"
        )
        own_member = await make_user(email="own.employee@example.com")
        other_member = await make_user(email="other.employee@example.com")
        await make_membership(
            user_id=own_member.id,
            organization_id=own_organization.id,
            role="member",
        )
        await make_membership(
            user_id=other_member.id,
            organization_id=other_organization.id,
            role="member",
        )

        response = client.get("/dashboard/employees")

        assert response.status_code == 200
        assert [employee["email"] for employee in response.json()] == [
            "own.employee@example.com"
        ]

    @pytest.mark.asyncio
    async def test_org_admins_are_not_listed_as_employees(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="dashboard-admin-filter@example.com",
            memberships=[("admin-filter-org", OrgRole.ADMIN)],
        )
        organization = await _get_organization_by_slug(
            db_session_maker, "admin-filter-org"
        )
        member = await make_user(email="listed.member@example.com")
        another_admin = await make_user(email="hidden.admin@example.com")
        await make_membership(
            user_id=member.id,
            organization_id=organization.id,
            role="member",
        )
        await make_membership(
            user_id=another_admin.id,
            organization_id=organization.id,
            role="admin",
        )

        response = client.get("/dashboard/employees")

        assert response.status_code == 200
        assert [employee["email"] for employee in response.json()] == [
            "listed.member@example.com"
        ]

    @pytest.mark.asyncio
    async def test_member_cannot_list_dashboard_employees(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="dashboard-member@example.com",
            memberships=[("member-dashboard-org", OrgRole.MEMBER)],
        )

        response = client.get("/dashboard/employees")

        assert response.status_code == 403
        assert response.json()["detail"] == "forbidden"

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_list_dashboard_employees(self, client):
        response = client.get("/dashboard/employees")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_org_admin_can_get_total_employee_count(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_organization,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="dashboard-summary-admin@example.com",
            memberships=[("summary-dashboard-org", OrgRole.ADMIN)],
        )
        organization = await _get_organization_by_slug(
            db_session_maker, "summary-dashboard-org"
        )
        other_organization = await make_organization(
            name="Other Summary Org", slug="other-summary-org"
        )
        member_a = await make_user(email="summary-a@example.com")
        member_b = await make_user(email="summary-b@example.com")
        another_admin = await make_user(email="summary-admin@example.com")
        other_member = await make_user(email="summary-other@example.com")
        await make_membership(
            user_id=member_a.id,
            organization_id=organization.id,
            role="member",
        )
        await make_membership(
            user_id=member_b.id,
            organization_id=organization.id,
            role="member",
        )
        await make_membership(
            user_id=another_admin.id,
            organization_id=organization.id,
            role="admin",
        )
        await make_membership(
            user_id=other_member.id,
            organization_id=other_organization.id,
            role="member",
        )

        response = client.get("/dashboard/summary")

        assert response.status_code == 200
        assert response.json() == {"total_employees": 2}

    @pytest.mark.asyncio
    async def test_member_cannot_get_dashboard_summary(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="dashboard-summary-member@example.com",
            memberships=[("summary-member-org", OrgRole.MEMBER)],
        )

        response = client.get("/dashboard/summary")

        assert response.status_code == 403
        assert response.json()["detail"] == "forbidden"

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_get_dashboard_summary(self, client):
        response = client.get("/dashboard/summary")

        assert response.status_code == 401
