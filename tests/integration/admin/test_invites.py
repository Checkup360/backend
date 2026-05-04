import pytest
from sqlalchemy import select

from app.models import InviteToken
from app.models.membership import OrgRole


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
            json={"email": "admin@example.com", "is_sysadmin": True},
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
    async def test_superuser_can_create_organization_invite(
        self,
        client,
        db_session_maker,
        make_organization,
        auth_scenario,
    ):
        await auth_scenario.register_and_login(
            email="superuser-org-invites@example.com",
            is_superuser=True,
        )
        organization = await make_organization(slug="super-org-invite")

        response = client.post(
            "/admin/invites",
            json={
                "organization_id": str(organization.id),
                "role": "admin",
                "max_uses": 3,
            },
        )

        assert response.status_code == 200
        async with db_session_maker() as session:
            invite = await session.scalar(
                select(InviteToken).where(InviteToken.token == response.json()["token"])
            )
        assert invite.organization_id == organization.id
        assert invite.role == OrgRole.ADMIN
        assert invite.max_uses == 3
        assert invite.is_sysadmin is False

    @pytest.mark.asyncio
    async def test_non_superuser_cannot_create_admin_invite(
        self, client, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="regular-admin-invites@example.com",
            is_superuser=False,
        )

        response = client.post(
            "/admin/invites",
            json={"email": "admin@example.com", "is_sysadmin": True},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_invite_role_requires_organization(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="superuser-role-check@example.com",
            is_superuser=True,
        )

        response = client.post("/admin/invites", json={"role": "admin"})

        assert response.status_code == 400
        assert response.json()["detail"] == "role_requires_organization"

    @pytest.mark.asyncio
    async def test_admin_invite_invalid_role_returns_validation_error(
        self, client, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="superuser-invalid-role@example.com",
            is_superuser=True,
        )

        response = client.post("/admin/invites", json={"role": "owner"})

        assert response.status_code == 422
