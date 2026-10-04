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


class TestSuperadminRemoval:
    @pytest.mark.asyncio
    async def test_superadmin_removes_another_superadmin(
        self, client, db_session_maker, auth_scenario, make_user, make_membership
    ):
        await auth_scenario.register_and_login(
            email="sa-remover@example.com",
            memberships=[("sa-removal-org", OrgRole.SUPERADMIN)],
        )
        org_id = await _organization_id(db_session_maker, "sa-removal-org")
        other = await make_user(email="sa-removed@example.com")
        await make_membership(
            user_id=other.id, organization_id=org_id, role="superadmin"
        )

        response = client.patch(
            f"/organizations/{org_id}/employees/{other.id}/roles",
            json={"roles": ["admin"]},
        )

        assert response.status_code == 200
        assert response.json()["roles"] == ["admin"]

    @pytest.mark.asyncio
    async def test_superadmin_deactivates_another_superadmin(
        self, client, db_session_maker, auth_scenario, make_user, make_membership
    ):
        await auth_scenario.register_and_login(
            email="sa-deactivator@example.com",
            memberships=[("sa-deactivate-org", OrgRole.SUPERADMIN)],
        )
        org_id = await _organization_id(db_session_maker, "sa-deactivate-org")
        other = await make_user(email="sa-deactivated@example.com")
        await make_membership(
            user_id=other.id, organization_id=org_id, role="superadmin"
        )

        response = client.delete(f"/organizations/{org_id}/employees/{other.id}")

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_superadmin_cannot_remove_own_superadmin_role(
        self, client, db_session_maker, auth_scenario, make_user, make_membership
    ):
        actor = await auth_scenario.register_and_login(
            email="sa-self@example.com",
            memberships=[("sa-self-org", OrgRole.SUPERADMIN)],
        )
        org_id = await _organization_id(db_session_maker, "sa-self-org")
        other = await make_user(email="sa-self-other@example.com")
        await make_membership(
            user_id=other.id, organization_id=org_id, role="superadmin"
        )

        patch_response = client.patch(
            f"/organizations/{org_id}/employees/{actor.id}/roles",
            json={"roles": ["admin"]},
        )
        delete_response = client.delete(f"/organizations/{org_id}/employees/{actor.id}")

        assert patch_response.status_code == 403
        assert patch_response.json()["detail"] == "cannot_remove_own_superadmin"
        assert delete_response.status_code == 403

    @pytest.mark.asyncio
    async def test_last_superadmin_cannot_be_removed(
        self, client, db_session_maker, auth_scenario, make_user, make_membership
    ):
        # Only a sysadmin can reach this case: a superadmin cannot remove
        # themselves, and removing another one means two exist.
        await auth_scenario.register_and_login(
            email="only-sa-org-admin@example.com",
            memberships=[("only-sa-org", OrgRole.ADMIN)],
        )
        org_id = await _organization_id(db_session_maker, "only-sa-org")
        owner = await make_user(email="only-sa@example.com")
        await make_membership(
            user_id=owner.id, organization_id=org_id, role="superadmin"
        )
        client.cookies.clear()
        await auth_scenario.register_and_login(
            email="sysadmin-last-sa@example.com",
            is_superuser=True,
        )

        response = client.patch(
            f"/organizations/{org_id}/employees/{owner.id}/roles",
            json={"roles": ["admin"]},
        )

        assert response.status_code == 409
        assert response.json()["detail"] == "cannot_remove_last_superadmin"

    @pytest.mark.asyncio
    async def test_regular_admin_cannot_remove_superadmin(
        self, client, db_session_maker, auth_scenario, make_user, make_membership
    ):
        await auth_scenario.register_and_login(
            email="plain-admin-sa@example.com",
            memberships=[("plain-admin-sa-org", OrgRole.ADMIN)],
        )
        org_id = await _organization_id(db_session_maker, "plain-admin-sa-org")
        target = await make_user(email="plain-admin-target-sa@example.com")
        await make_membership(
            user_id=target.id, organization_id=org_id, role="superadmin"
        )

        response = client.patch(
            f"/organizations/{org_id}/employees/{target.id}/roles",
            json={"roles": ["admin"]},
        )

        assert response.status_code == 403
