import pytest
from sqlalchemy import select

from app.domain.value_objects.org_role import OrgRole
from app.infrastructure.persistence.models import Organization


async def _get_organization_by_slug(db_session_maker, slug: str) -> Organization:
    async with db_session_maker() as session:
        organization = await session.scalar(
            select(Organization).where(Organization.slug == slug)
        )
        assert organization is not None
        return organization


class TestOrganizationEmployees:
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

        response = client.get(f"/organizations/{organization.id}/employees?role=member")

        assert response.status_code == 200
        data = response.json()
        assert [employee["email"] for employee in data] == [
            "ana.employee@example.com",
            "zoe.employee@example.com",
        ]
        assert all(employee["roles"] == ["member"] for employee in data)
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

        response = client.get(
            f"/organizations/{own_organization.id}/employees?role=member"
        )

        assert response.status_code == 200
        assert [employee["email"] for employee in response.json()] == [
            "own.employee@example.com"
        ]

    @pytest.mark.asyncio
    async def test_org_admin_can_filter_admins_and_members(
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

        members_response = client.get(
            f"/organizations/{organization.id}/employees?role=member"
        )
        admins_response = client.get(
            f"/organizations/{organization.id}/employees?role=admin"
        )

        assert members_response.status_code == 200
        assert [employee["email"] for employee in members_response.json()] == [
            "listed.member@example.com"
        ]
        assert admins_response.status_code == 200
        assert [employee["email"] for employee in admins_response.json()] == [
            "dashboard-admin-filter@example.com",
            "hidden.admin@example.com",
        ]

    @pytest.mark.asyncio
    async def test_org_admin_can_filter_multiple_roles(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="dashboard-multi-role-admin@example.com",
            memberships=[("multi-role-org", OrgRole.ADMIN)],
        )
        organization = await _get_organization_by_slug(
            db_session_maker, "multi-role-org"
        )
        member = await make_user(email="multi.member@example.com")
        await make_membership(
            user_id=member.id,
            organization_id=organization.id,
            role="member",
        )

        response = client.get(
            f"/organizations/{organization.id}/employees?role=member&role=admin"
        )

        assert response.status_code == 200
        assert [employee["email"] for employee in response.json()] == [
            "dashboard-multi-role-admin@example.com",
            "multi.member@example.com",
        ]

    @pytest.mark.asyncio
    async def test_default_lists_all_employee_roles(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="dashboard-all-roles-admin@example.com",
            memberships=[("all-roles-org", OrgRole.ADMIN)],
        )
        organization = await _get_organization_by_slug(
            db_session_maker, "all-roles-org"
        )
        member = await make_user(email="all-roles.member@example.com")
        await make_membership(
            user_id=member.id,
            organization_id=organization.id,
            role="member",
        )

        response = client.get(f"/organizations/{organization.id}/employees")

        assert response.status_code == 200
        assert [employee["email"] for employee in response.json()] == [
            "all-roles.member@example.com",
            "dashboard-all-roles-admin@example.com",
        ]

    @pytest.mark.asyncio
    async def test_admin_cannot_list_another_organizations_employees(
        self,
        client,
        auth_scenario,
        make_user,
        make_organization,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="dashboard-wrong-org-admin@example.com",
            memberships=[("wrong-org-admin-org", OrgRole.ADMIN)],
        )
        other_organization = await make_organization(
            name="Wrong Org Target", slug="wrong-org-target"
        )
        other_member = await make_user(email="wrong-org.member@example.com")
        await make_membership(
            user_id=other_member.id,
            organization_id=other_organization.id,
            role="member",
        )

        response = client.get(f"/organizations/{other_organization.id}/employees")

        assert response.status_code == 403
        assert response.json()["detail"] == "forbidden"

    @pytest.mark.asyncio
    async def test_member_cannot_list_organization_employees(
        self, client, db_session_maker, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="dashboard-member@example.com",
            memberships=[("member-dashboard-org", OrgRole.MEMBER)],
        )
        organization = await _get_organization_by_slug(
            db_session_maker, "member-dashboard-org"
        )

        response = client.get(f"/organizations/{organization.id}/employees")

        assert response.status_code == 403
        assert response.json()["detail"] == "forbidden"

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_list_organization_employees(self, client):
        response = client.get(
            "/organizations/00000000-0000-0000-0000-000000000000/employees"
        )

        assert response.status_code == 401
