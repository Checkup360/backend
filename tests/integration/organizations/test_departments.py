import pytest
from sqlalchemy import select

from app.domain.value_objects.org_role import OrgRole
from app.infrastructure.persistence.models import InviteToken, Membership, Organization


async def _get_organization_by_slug(db_session_maker, slug: str) -> Organization:
    async with db_session_maker() as session:
        organization = await session.scalar(
            select(Organization).where(Organization.slug == slug)
        )
        assert organization is not None
        return organization


class TestOrganizationDepartments:
    @pytest.mark.asyncio
    async def test_org_admin_can_create_list_and_rename_department(
        self, client, db_session_maker, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="departments-admin@example.com",
            memberships=[("departments-org", OrgRole.ADMIN)],
        )
        organization = await _get_organization_by_slug(
            db_session_maker, "departments-org"
        )

        create_response = client.post(
            f"/organizations/{organization.id}/departments",
            json={"name": "People Operations"},
        )

        assert create_response.status_code == 201
        created = create_response.json()
        assert created["name"] == "People Operations"
        assert created["slug"] == "people-operations"

        list_response = client.get(f"/organizations/{organization.id}/departments")
        assert list_response.status_code == 200
        assert [department["name"] for department in list_response.json()] == [
            "People Operations"
        ]

        rename_response = client.patch(
            f"/organizations/{organization.id}/departments/{created['id']}",
            json={"name": "Clinical Team"},
        )
        assert rename_response.status_code == 200
        assert rename_response.json()["slug"] == "clinical-team"

    @pytest.mark.asyncio
    async def test_org_admin_cannot_create_duplicate_department_slug(
        self, client, db_session_maker, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="departments-duplicate@example.com",
            memberships=[("duplicate-departments-org", OrgRole.ADMIN)],
        )
        organization = await _get_organization_by_slug(
            db_session_maker, "duplicate-departments-org"
        )
        first = client.post(
            f"/organizations/{organization.id}/departments",
            json={"name": "Operations"},
        )
        assert first.status_code == 201

        duplicate = client.post(
            f"/organizations/{organization.id}/departments",
            json={"name": "Operations"},
        )

        assert duplicate.status_code == 409
        assert duplicate.json()["detail"] == "department_slug_already_exists"

    @pytest.mark.asyncio
    async def test_member_cannot_manage_departments(
        self, client, db_session_maker, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="departments-member@example.com",
            memberships=[("member-departments-org", OrgRole.MEMBER)],
        )
        organization = await _get_organization_by_slug(
            db_session_maker, "member-departments-org"
        )

        response = client.post(
            f"/organizations/{organization.id}/departments",
            json={"name": "People"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "forbidden"

    @pytest.mark.asyncio
    async def test_delete_assigned_department_returns_conflict(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_department,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="departments-delete@example.com",
            memberships=[("delete-departments-org", OrgRole.ADMIN)],
        )
        organization = await _get_organization_by_slug(
            db_session_maker, "delete-departments-org"
        )
        department = await make_department(organization_id=organization.id)
        member = await make_user(email="assigned.department@example.com")
        await make_membership(
            user_id=member.id,
            organization_id=organization.id,
            role="member",
            department_id=department.id,
        )

        response = client.delete(
            f"/organizations/{organization.id}/departments/{department.id}"
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "department_in_use"

    @pytest.mark.asyncio
    async def test_invite_member_with_department_assigns_membership(
        self, client, db_session_maker, auth_scenario, make_department
    ):
        await auth_scenario.register_and_login(
            email="department-invite-admin@example.com",
            memberships=[("department-invite-org", OrgRole.ADMIN)],
        )
        organization = await _get_organization_by_slug(
            db_session_maker, "department-invite-org"
        )
        department = await make_department(organization_id=organization.id)

        invite_response = client.post(
            "/invites/organization",
            json={"role": "member", "department_id": str(department.id)},
        )
        assert invite_response.status_code == 200

        client.cookies.clear()
        redeem_response = client.post(
            f"/invites/{invite_response.json()['token']}/redeem",
            json={
                "email": "department-member@example.com",
                "password": "SuperSecure123!",
            },
            follow_redirects=False,
        )
        assert redeem_response.status_code == 303

        async with db_session_maker() as session:
            membership = await session.scalar(
                select(Membership).where(Membership.department_id == department.id)
            )
            assert membership is not None

    @pytest.mark.asyncio
    async def test_invite_member_without_department_creates_unassigned_invite(
        self, client, db_session_maker, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="department-optional-admin@example.com",
            memberships=[("department-optional-org", OrgRole.ADMIN)],
        )

        response = client.post("/invites/organization", json={"role": "member"})

        assert response.status_code == 200
        async with db_session_maker() as session:
            invite = await session.scalar(
                select(InviteToken).where(InviteToken.token == response.json()["token"])
            )
            assert invite.department_id is None

    @pytest.mark.asyncio
    async def test_employees_returns_department_or_null(
        self,
        client,
        db_session_maker,
        auth_scenario,
        make_user,
        make_department,
        make_membership,
    ):
        await auth_scenario.register_and_login(
            email="department-employees-admin@example.com",
            memberships=[("department-employees-org", OrgRole.ADMIN)],
        )
        organization = await _get_organization_by_slug(
            db_session_maker, "department-employees-org"
        )
        department = await make_department(organization_id=organization.id)
        assigned = await make_user(email="assigned@example.com")
        unassigned = await make_user(email="unassigned@example.com")
        await make_membership(
            user_id=assigned.id,
            organization_id=organization.id,
            role="member",
            department_id=department.id,
        )
        await make_membership(
            user_id=unassigned.id,
            organization_id=organization.id,
            role="member",
        )

        response = client.get(f"/organizations/{organization.id}/employees?role=member")

        assert response.status_code == 200
        employees = {employee["email"]: employee for employee in response.json()}
        assert employees["assigned@example.com"]["department"]["name"] == "People"
        assert employees["unassigned@example.com"]["department"] is None
