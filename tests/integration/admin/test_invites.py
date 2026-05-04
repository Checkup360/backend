import pytest
from sqlalchemy import select

from app.models import InviteToken


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
