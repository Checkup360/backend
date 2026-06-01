import pytest
from sqlalchemy import select

from app.persistence.models import InviteToken


class TestAdminInvites:
    @pytest.mark.asyncio
    async def test_superuser_can_create_sysadmin_invite(
        self, client, db_session_maker, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="superuser-admin-invites@example.com",
            is_superuser=True,
        )

        response = client.post(
            "/admin/invites",
            json={"email": "admin@example.com"},
        )

        assert response.status_code == 200
        async with db_session_maker() as session:
            invite = await session.scalar(
                select(InviteToken).where(InviteToken.token == response.json()["token"])
            )
        assert invite.email == "admin@example.com"
        assert invite.is_sysadmin is True
        assert invite.organization_id is None
        assert invite.role is None

    @pytest.mark.asyncio
    async def test_non_superuser_cannot_create_sysadmin_invite(
        self, client, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="regular-admin-invites@example.com",
            is_superuser=False,
        )

        response = client.post(
            "/admin/invites",
            json={"email": "admin@example.com"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_superuser_can_delete_sysadmin_invites_only(
        self, client, db_session_maker, make_invite, make_organization, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="superuser-delete-admin-invites@example.com",
            is_superuser=True,
        )
        organization = await make_organization(slug="delete-admin-invites-org")
        sysadmin_invite = await make_invite(
            email="delete-sysadmin@example.com",
            is_sysadmin=True,
        )
        org_invite = await make_invite(
            email="keep-org@example.com",
            organization_id=organization.id,
        )

        response = client.request(
            "DELETE",
            "/admin/invites",
            json={"ids": [str(sysadmin_invite.id), str(org_invite.id)]},
        )

        assert response.status_code == 200
        assert response.json()["deleted_count"] == 1
        async with db_session_maker() as session:
            deleted = await session.get(InviteToken, sysadmin_invite.id)
            kept = await session.get(InviteToken, org_invite.id)
        assert deleted is None
        assert kept is not None
