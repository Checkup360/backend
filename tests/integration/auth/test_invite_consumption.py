import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.manager import UserManager
from app.models import User, Organization
from app.models.invite import InviteToken
from app.domain.entities.org_role import OrgRole
from app.models.membership import Membership


async def create_user(
    db: AsyncSession,
    *,
    email: str,
    is_superuser: bool = False,
) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password="hash123",
        is_superuser=is_superuser,
    )
    db.add(user)
    await db.flush()
    return user


async def create_organization(
    db: AsyncSession,
    *,
    name: str,
    slug: str,
) -> Organization:
    org = Organization(id=uuid.uuid4(), name=name, slug=slug)
    db.add(org)
    await db.flush()
    return org


async def create_invite(
    db: AsyncSession,
    *,
    token: str,
    organization_id=None,
    role: OrgRole | None = OrgRole.MEMBER,
    is_sysadmin: bool = False,
    max_uses: int = 1,
    uses: int = 0,
) -> InviteToken:
    invite = InviteToken(
        id=uuid.uuid4(),
        token=token,
        email=None,
        organization_id=organization_id,
        role=role,
        is_sysadmin=is_sysadmin,
        max_uses=max_uses,
        uses=uses,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invite)
    await db.flush()
    return invite


async def get_membership(
    db: AsyncSession, *, user_id: uuid.UUID, organization_id: uuid.UUID
) -> Membership | None:
    return await db.scalar(
        select(Membership).where(
            Membership.user_id == user_id,
            Membership.organization_id == organization_id,
        )
    )


@pytest.mark.asyncio
class TestInviteConsumptionIntegration:
    async def test_new_user_joins_org_with_invite(
        self, db: AsyncSession, user_manager: UserManager
    ):
        org = await create_organization(db, name="Test Org", slug="test-org")
        invite = await create_invite(
            db,
            token="new-user-invite",
            organization_id=org.id,
            role=OrgRole.MEMBER,
        )
        user = await create_user(db, email="newuser@test.com")
        await db.commit()

        await user_manager._consume_invite_by_id(invite.id, user)

        membership = await get_membership(db, user_id=user.id, organization_id=org.id)
        assert membership is not None
        assert membership.role == OrgRole.MEMBER
        invite_db = await db.get(InviteToken, invite.id)
        assert invite_db.uses == 1

    async def test_existing_admin_not_downgraded(
        self, db: AsyncSession, user_manager: UserManager
    ):
        org = await create_organization(db, name="Admin Test Org", slug="admin-org")
        user = await create_user(db, email="admin@test.com")
        db.add(
            Membership(
                user_id=user.id,
                organization_id=org.id,
                role=OrgRole.ADMIN,
            )
        )
        invite = await create_invite(
            db,
            token="member-invite",
            organization_id=org.id,
            role=OrgRole.MEMBER,
        )
        await db.commit()

        await user_manager._consume_invite_by_id(invite.id, user)

        membership = await db.get(Membership, (user.id, org.id))
        assert membership.role == OrgRole.ADMIN

        memberships = await db.scalars(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.organization_id == org.id,
            )
        )
        assert len(list(memberships)) == 1

        invite_db = await db.get(InviteToken, invite.id)
        assert invite_db.uses == 0

    async def test_invite_uses_incremented_correctly(
        self, db: AsyncSession, user_manager: UserManager
    ):
        org = await create_organization(db, name="Multi Use Org", slug="multi-use")
        invite = await create_invite(
            db,
            token="multi-use-token",
            organization_id=org.id,
            role=OrgRole.MEMBER,
            max_uses=3,
        )
        await db.commit()

        for i in range(3):
            user = await create_user(db, email=f"user{i}@test.com")
            await user_manager._consume_invite_by_id(invite.id, user)

        invite_db = await db.get(InviteToken, invite.id)
        assert invite_db.uses == 3
        assert invite_db.is_exhausted is True

    async def test_sysadmin_invite_sets_superuser(
        self, db: AsyncSession, user_manager: UserManager
    ):
        user = await create_user(
            db,
            email="future-admin@test.com",
            is_superuser=False,
        )
        invite = await create_invite(
            db,
            token="sysadmin-token",
            organization_id=None,
            role=None,
            is_sysadmin=True,
        )
        await db.commit()

        await user_manager._consume_invite_by_id(invite.id, user)

        user_db = await db.get(User, user.id)
        assert user_db.is_superuser is True
        invite_db = await db.get(InviteToken, invite.id)
        assert invite_db.uses == 1

    async def test_invite_with_default_member_role(
        self, db: AsyncSession, user_manager: UserManager
    ):
        org = await create_organization(
            db, name="Default Role Org", slug="default-role"
        )
        user = await create_user(db, email="default@test.com")
        invite = await create_invite(
            db,
            token="default-role-token",
            organization_id=org.id,
            role=None,
        )
        await db.commit()

        await user_manager._consume_invite_by_id(invite.id, user)

        membership = await get_membership(db, user_id=user.id, organization_id=org.id)
        assert membership.role == OrgRole.MEMBER

    async def test_exhausted_invite_does_nothing(
        self, db: AsyncSession, user_manager: UserManager
    ):
        org = await create_organization(db, name="Exhausted Org", slug="exhausted")
        user = await create_user(db, email="exhausted@test.com")
        invite = await create_invite(
            db,
            token="exhausted-token",
            organization_id=org.id,
            role=OrgRole.MEMBER,
            uses=1,
        )
        await db.commit()

        await user_manager._consume_invite_by_id(invite.id, user)

        membership = await get_membership(db, user_id=user.id, organization_id=org.id)
        assert membership is None

        invite_db = await db.get(InviteToken, invite.id)
        assert invite_db.uses == 1

    async def test_multiple_users_same_org_invite(
        self, db: AsyncSession, user_manager: UserManager
    ):
        org = await create_organization(db, name="Shared Org", slug="shared")
        invite = await create_invite(
            db,
            token="shared-invite",
            organization_id=org.id,
            role=OrgRole.MEMBER,
            max_uses=2,
        )
        await db.commit()

        users = []
        for i in range(2):
            user = await create_user(db, email=f"shared-user{i}@test.com")
            users.append(user)

        for user in users:
            await user_manager._consume_invite_by_id(invite.id, user)

        memberships = await db.scalars(
            select(Membership).where(Membership.organization_id == org.id)
        )
        memberships_list = list(memberships)
        assert len(memberships_list) == 2

        invite_db = await db.get(InviteToken, invite.id)
        assert invite_db is not None
        assert invite_db.uses == 2
        assert invite_db.is_exhausted is True
