import pytest
from sqlalchemy import select

from app.models import InviteToken, Membership
from app.models.membership import OrgRole


class TestOrgInvites:
    @pytest.mark.asyncio
    async def test_org_admin_can_create_member_invite(
        self,
        client,
        db_session_maker,
        make_user,
        make_organization,
        override_current_user,
    ):
        user = await make_user()
        organization = await make_organization(slug="member-invite")
        async with db_session_maker() as session:
            session.add(
                Membership(
                    user_id=user.id,
                    organization_id=organization.id,
                    role=OrgRole.ADMIN,
                )
            )
            await session.commit()
        override_current_user(user)

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
        make_user,
        make_organization,
        override_current_user,
    ):
        user = await make_user()
        organization = await make_organization(slug="admin-invite")
        async with db_session_maker() as session:
            session.add(
                Membership(
                    user_id=user.id,
                    organization_id=organization.id,
                    role=OrgRole.ADMIN,
                )
            )
            await session.commit()
        override_current_user(user)

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
        make_user,
        make_organization,
        override_current_user,
    ):
        user = await make_user()
        organization = await make_organization(slug="member-denied")
        async with db_session_maker() as session:
            session.add(
                Membership(
                    user_id=user.id,
                    organization_id=organization.id,
                    role=OrgRole.MEMBER,
                )
            )
            await session.commit()
        override_current_user(user)

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
        make_user,
        make_organization,
        override_current_user,
    ):
        user = await make_user()
        organization = await make_organization(slug="invalid-org-role")
        async with db_session_maker() as session:
            session.add(
                Membership(
                    user_id=user.id,
                    organization_id=organization.id,
                    role=OrgRole.ADMIN,
                )
            )
            await session.commit()
        override_current_user(user)

        response = client.post(
            "/invites/organization",
            json={
                "organization_id": str(organization.id),
                "role": "owner",
            },
        )

        assert response.status_code == 422
