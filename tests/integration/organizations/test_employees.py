import uuid

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

    @pytest.mark.asyncio
    async def test_org_admin_can_get_employee_assessments(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="assessments-admin@example.com",
            memberships=[("assessments-org", OrgRole.ADMIN)],
        )
        organization = await _get_organization_by_slug(
            db_session_maker, "assessments-org"
        )
        employee = await make_user(email="assessed.employee@example.com")
        await make_membership(
            user_id=employee.id,
            organization_id=organization.id,
            role="member",
        )

        response = client.get(
            f"/organizations/{organization.id}/employees/{employee.id}/assessments"
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    @pytest.mark.asyncio
    async def test_admin_cannot_get_other_organization_employee_assessments(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_organization,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="org-a-admin@example.com",
            memberships=[("org-a", OrgRole.ADMIN)],
        )
        org_a = await _get_organization_by_slug(db_session_maker, "org-a")
        org_b = await make_organization(name="Org B", slug="org-b")
        employee_b = await make_user(email="emp-b@example.com")
        await make_membership(
            user_id=employee_b.id,
            organization_id=org_b.id,
            role="member",
        )

        response = client.get(
            f"/organizations/{org_a.id}/employees/{employee_b.id}/assessments"
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "not_found"

    @pytest.mark.asyncio
    async def test_admin_getting_nonexistent_employee_assessments_returns_404(
        self,
        client,
        db_session_maker,
        auth_scenario,
    ):
        await auth_scenario.register_and_login(
            email="nonexistent-emp-admin@example.com",
            memberships=[("nonexistent-emp-org", OrgRole.ADMIN)],
        )
        organization = await _get_organization_by_slug(
            db_session_maker, "nonexistent-emp-org"
        )
        random_user_id = uuid.uuid4()

        response = client.get(
            f"/organizations/{organization.id}/employees/{random_user_id}/assessments"
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "not_found"

    @pytest.mark.asyncio
    async def test_superuser_can_get_any_employee_assessments(
        self,
        client,
        auth_scenario,
        make_organization,
        make_user,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="superuser-assessments@example.com",
            is_superuser=True,
        )
        organization = await make_organization(
            name="Superuser Target Org", slug="su-target-org"
        )
        employee = await make_user(email="su-assessed.employee@example.com")
        await make_membership(
            user_id=employee.id,
            organization_id=organization.id,
            role="member",
        )

        response = client.get(
            f"/organizations/{organization.id}/employees/{employee.id}/assessments"
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    @pytest.mark.asyncio
    async def test_admin_cannot_modify_admin_or_superadmin_roles(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="regular-admin@example.com",
            memberships=[("perm-org", OrgRole.ADMIN)],
        )
        organization = await _get_organization_by_slug(db_session_maker, "perm-org")
        target_admin = await make_user(email="target-admin@example.com")
        await make_membership(
            user_id=target_admin.id,
            organization_id=organization.id,
            role="admin",
        )

        response = client.patch(
            f"/organizations/{organization.id}/employees/{target_admin.id}/roles",
            json={"roles": ["member"]},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_cannot_grant_admin_or_superadmin_roles(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="regular-admin-grant@example.com",
            memberships=[("grant-org", OrgRole.ADMIN)],
        )
        organization = await _get_organization_by_slug(db_session_maker, "grant-org")
        target_member = await make_user(email="target-member@example.com")
        await make_membership(
            user_id=target_member.id,
            organization_id=organization.id,
            role="member",
        )

        response = client.patch(
            f"/organizations/{organization.id}/employees/{target_member.id}/roles",
            json={"roles": ["admin"]},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_modify_member_or_content_manager_roles(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="regular-admin-mod@example.com",
            memberships=[("mod-org", OrgRole.ADMIN)],
        )
        organization = await _get_organization_by_slug(db_session_maker, "mod-org")
        target_member = await make_user(email="target-mod-member@example.com")
        await make_membership(
            user_id=target_member.id,
            organization_id=organization.id,
            role="member",
        )

        response = client.patch(
            f"/organizations/{organization.id}/employees/{target_member.id}/roles",
            json={"roles": ["content_manager"]},
        )
        assert response.status_code == 200
        assert response.json()["roles"] == ["content_manager"]

    @pytest.mark.asyncio
    async def test_superadmin_can_remove_admin_role(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="superadmin-actor@example.com",
            memberships=[("sa-mod-org", OrgRole.SUPERADMIN)],
        )
        organization = await _get_organization_by_slug(db_session_maker, "sa-mod-org")
        target_admin = await make_user(email="target-admin-demote@example.com")
        await make_membership(
            user_id=target_admin.id,
            organization_id=organization.id,
            role="admin",
        )

        response = client.patch(
            f"/organizations/{organization.id}/employees/{target_admin.id}/roles",
            json={"roles": ["member"]},
        )
        assert response.status_code == 200
        assert response.json()["roles"] == ["member"]

    @pytest.mark.asyncio
    async def test_employee_losing_member_role_becomes_inactive_and_loses_member_portal_access(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="org-admin-deact@example.com",
            memberships=[("deact-org", OrgRole.ADMIN)],
        )
        organization = await _get_organization_by_slug(db_session_maker, "deact-org")

        employee_user = await make_user(email="employee-to-deact@example.com")
        await make_membership(
            user_id=employee_user.id,
            organization_id=organization.id,
            role="member",
        )

        delete_resp = client.delete(
            f"/organizations/{organization.id}/employees/{employee_user.id}"
        )
        assert delete_resp.status_code == 204

        list_resp = client.get(f"/organizations/{organization.id}/employees")
        assert list_resp.status_code == 200
        employees = list_resp.json()
        deactivated = next(e for e in employees if e["id"] == str(employee_user.id))
        assert deactivated["status"] == "inactive"
        assert deactivated["roles"] == []

    @pytest.mark.asyncio
    async def test_employee_with_roles_but_not_member_has_no_status(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="org-admin-non-member@example.com",
            memberships=[("non-member-org", OrgRole.ADMIN)],
        )
        organization = await _get_organization_by_slug(
            db_session_maker, "non-member-org"
        )
        content_manager = await make_user(email="content-manager-only@example.com")
        await make_membership(
            user_id=content_manager.id,
            organization_id=organization.id,
            role="content_manager",
        )

        response = client.get(f"/organizations/{organization.id}/employees")

        assert response.status_code == 200
        employee = next(
            e for e in response.json() if e["id"] == str(content_manager.id)
        )
        assert employee["roles"] == ["content_manager"]
        assert employee["status"] is None
