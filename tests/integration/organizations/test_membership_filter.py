import pytest
from sqlalchemy import select

from app.domain.value_objects.org_role import OrgRole
from app.infrastructure.persistence.models import Organization


async def _organization_id(db_session_maker, slug: str):
    async with db_session_maker() as session:
        organization = await session.scalar(
            select(Organization).where(Organization.slug == slug)
        )
        assert organization is not None
        return organization.id


async def _setup(client, db_session_maker, auth_scenario, make_user, make_membership):
    """Organization with an admin, an active member and two deactivated users."""
    await auth_scenario.register_and_login(
        email="membership-admin@example.com",
        memberships=[("membership-filter-org", OrgRole.ADMIN)],
    )
    org_id = await _organization_id(db_session_maker, "membership-filter-org")
    users = {}
    for email, role in [
        ("active-member@example.com", "member"),
        ("former-member@example.com", "member"),
        ("former-content@example.com", "content_manager"),
    ]:
        user = await make_user(email=email)
        await make_membership(user_id=user.id, organization_id=org_id, role=role)
        users[email] = user
    for email in ("former-member@example.com", "former-content@example.com"):
        response = client.delete(f"/organizations/{org_id}/employees/{users[email].id}")
        assert response.status_code == 204
    return org_id


def _emails(response) -> set[str]:
    assert response.status_code == 200
    return {employee["email"] for employee in response.json()}


class TestMembershipFilter:
    @pytest.mark.asyncio
    async def test_default_lists_active_and_inactive_users(
        self, client, db_session_maker, auth_scenario, make_user, make_membership
    ):
        org_id = await _setup(
            client, db_session_maker, auth_scenario, make_user, make_membership
        )

        emails = _emails(client.get(f"/organizations/{org_id}/employees"))

        assert {
            "membership-admin@example.com",
            "active-member@example.com",
            "former-member@example.com",
            "former-content@example.com",
        } <= emails

    @pytest.mark.asyncio
    async def test_active_excludes_users_without_roles(
        self, client, db_session_maker, auth_scenario, make_user, make_membership
    ):
        org_id = await _setup(
            client, db_session_maker, auth_scenario, make_user, make_membership
        )

        emails = _emails(
            client.get(f"/organizations/{org_id}/employees?membership=active")
        )

        assert emails == {"membership-admin@example.com", "active-member@example.com"}

    @pytest.mark.asyncio
    async def test_inactive_lists_only_users_without_roles(
        self, client, db_session_maker, auth_scenario, make_user, make_membership
    ):
        org_id = await _setup(
            client, db_session_maker, auth_scenario, make_user, make_membership
        )

        emails = _emails(
            client.get(f"/organizations/{org_id}/employees?membership=inactive")
        )

        assert emails == {"former-member@example.com", "former-content@example.com"}

    @pytest.mark.asyncio
    async def test_members_list_excludes_deactivated_users(
        self, client, db_session_maker, auth_scenario, make_user, make_membership
    ):
        org_id = await _setup(
            client, db_session_maker, auth_scenario, make_user, make_membership
        )

        emails = _emails(client.get(f"/organizations/{org_id}/employees?role=member"))

        assert emails == {"active-member@example.com"}

    @pytest.mark.asyncio
    async def test_summary_does_not_count_deactivated_users_as_employees(
        self, client, db_session_maker, auth_scenario, make_user, make_membership
    ):
        org_id = await _setup(
            client, db_session_maker, auth_scenario, make_user, make_membership
        )
        # The summary is a backoffice endpoint, reserved to sysadmins
        client.cookies.clear()
        await auth_scenario.register_and_login(
            email="membership-sysadmin@example.com", is_superuser=True
        )

        response = client.get(f"/organizations/{org_id}/summary")

        assert response.status_code == 200
        assert response.json()["total_employees"] == 1

    @pytest.mark.asyncio
    async def test_invalid_membership_value_is_rejected(
        self, client, db_session_maker, auth_scenario, make_user, make_membership
    ):
        org_id = await _setup(
            client, db_session_maker, auth_scenario, make_user, make_membership
        )

        response = client.get(f"/organizations/{org_id}/employees?membership=gone")

        assert response.status_code == 422
