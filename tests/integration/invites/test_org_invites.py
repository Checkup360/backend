import pytest
from sqlalchemy import select

from app.persistence.models import InviteToken, Organization
from app.domain.entities.org_role import OrgRole


class TestOrgInvites:
    @pytest.mark.asyncio
    async def test_org_admin_can_create_member_invite(
        self,
        client,
        db_session_maker,
        auth_scenario,
    ):
        await auth_scenario.register_and_login(
            email="org-admin-member-invite@example.com",
            memberships=[("member-invite", OrgRole.ADMIN)],
        )
        async with db_session_maker() as session:
            organization = await session.scalar(
                select(Organization).where(Organization.slug == "member-invite")
            )

        response = client.post(
            "/invites/organization",
            json={
                "email": "new@example.com",
                "organization_id": str(organization.id),
                "role": "member",
            },
        )

        assert response.status_code == 200
        token = response.json()["token"]
        async with db_session_maker() as session:
            invite = await session.scalar(
                select(InviteToken).where(InviteToken.token == token)
            )
        assert invite.organization_id == organization.id
        assert invite.role == OrgRole.MEMBER
        assert invite.email == "new@example.com"
        assert invite.is_sysadmin is False

    @pytest.mark.asyncio
    async def test_org_admin_can_create_admin_invite(
        self,
        client,
        db_session_maker,
        auth_scenario,
    ):
        await auth_scenario.register_and_login(
            email="org-admin-admin-invite@example.com",
            memberships=[("admin-invite", OrgRole.ADMIN)],
        )
        async with db_session_maker() as session:
            organization = await session.scalar(
                select(Organization).where(Organization.slug == "admin-invite")
            )

        response = client.post(
            "/invites/organization",
            json={
                "organization_id": str(organization.id),
                "role": "admin",
            },
        )

        assert response.status_code == 200
        async with db_session_maker() as session:
            invite = await session.scalar(
                select(InviteToken).where(InviteToken.token == response.json()["token"])
            )
        assert invite.role == OrgRole.ADMIN

    @pytest.mark.asyncio
    async def test_member_cannot_create_org_invite(
        self,
        client,
        db_session_maker,
        auth_scenario,
    ):
        await auth_scenario.register_and_login(
            email="org-member-denied@example.com",
            memberships=[("member-denied", OrgRole.MEMBER)],
        )
        async with db_session_maker() as session:
            organization = await session.scalar(
                select(Organization).where(Organization.slug == "member-denied")
            )

        response = client.post(
            "/invites/organization",
            json={
                "organization_id": str(organization.id),
                "role": "member",
            },
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_invalid_role_returns_validation_error(
        self,
        client,
        db_session_maker,
        auth_scenario,
    ):
        await auth_scenario.register_and_login(
            email="org-invalid-role@example.com",
            memberships=[("invalid-org-role", OrgRole.ADMIN)],
        )
        async with db_session_maker() as session:
            organization = await session.scalar(
                select(Organization).where(Organization.slug == "invalid-org-role")
            )

        response = client.post(
            "/invites/organization",
            json={
                "organization_id": str(organization.id),
                "role": "owner",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_sysadmin_without_org_membership_can_create_org_invite(
        self,
        client,
        db_session_maker,
        make_organization,
        auth_scenario,
    ):
        """Test that a sysadmin without org membership can create org invites."""
        await auth_scenario.register_and_login(
            email="sysadmin-no-org@example.com",
            is_superuser=True,
        )
        organization = await make_organization(slug="sysadmin-no-membership-org")

        response = client.post(
            "/invites/organization",
            json={
                "email": "newuser@example.com",
                "organization_id": str(organization.id),
                "role": "member",
            },
        )

        assert response.status_code == 200
        token = response.json()["token"]
        async with db_session_maker() as session:
            invite = await session.scalar(
                select(InviteToken).where(InviteToken.token == token)
            )
        assert invite.organization_id == organization.id
        assert invite.role == OrgRole.MEMBER
        assert invite.is_sysadmin is False
