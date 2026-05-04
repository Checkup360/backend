import pytest
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import User, Organization
from app.models.invite import InviteToken
from app.models.membership import Membership, OrgRole
from app.auth.manager import UserManager


@pytest.mark.asyncio
class TestInviteConsumptionIntegration:
    """Integration tests for invite consumption with a real database."""

    async def test_new_user_joins_org_with_invite(
        self, db: AsyncSession, user_manager: UserManager, request_for_integration
    ):
        """New user joins the organization via invite."""
        # Setup: create organization
        org = Organization(id=uuid.uuid4(), name="Test Org", slug="test-org")
        db.add(org)
        await db.flush()

        # Create invite for the organization
        invite = InviteToken(
            id=uuid.uuid4(),
            token="new-user-invite",
            email=None,
            organization_id=org.id,
            role=OrgRole.MEMBER,
            is_sysadmin=False,
            max_uses=1,
            uses=0,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(invite)
        await db.flush()

        # Create user
        user = User(
            id=uuid.uuid4(),
            email="newuser@test.com",
            hashed_password="hash123",
        )
        db.add(user)
        await db.commit()

        # Action: consume invite
        await user_manager._consume_invite_by_id(
            request_for_integration, invite.id, user
        )

        # Assertions
        membership = await db.scalar(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.organization_id == org.id,
            )
        )
        assert membership is not None, "Membership debería existir"
        assert membership.role == OrgRole.MEMBER, "Rol debería ser MEMBER"

        # Verify the invite was consumed
        invite_db = await db.get(InviteToken, invite.id)
        assert invite_db.uses == 1, "Uses debería incrementarse"

    async def test_existing_admin_not_downgraded(
        self, db: AsyncSession, user_manager: UserManager, request_for_integration
    ):
        org = Organization(id=uuid.uuid4(), name="Admin Test Org", slug="admin-org")
        db.add(org)
        await db.flush()

        user = User(
            id=uuid.uuid4(),
            email="admin@test.com",
            hashed_password="hash123",
        )
        db.add(user)
        await db.flush()

        admin_membership = Membership(
            user_id=user.id,
            organization_id=org.id,
            role=OrgRole.ADMIN,
        )
        db.add(admin_membership)
        await db.flush()

        user = await db.get(User, user.id)

        invite = InviteToken(
            id=uuid.uuid4(),
            token="member-invite",
            email=None,
            organization_id=org.id,
            role=OrgRole.MEMBER,
            is_sysadmin=False,
            max_uses=1,
            uses=0,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(invite)
        await db.commit()

        await user_manager._consume_invite_by_id(
            request_for_integration, invite.id, user
        )

        membership = await db.get(Membership, (user.id, org.id))
        assert membership.role == OrgRole.ADMIN, "Rol debería mantenerse ADMIN"

        memberships = await db.scalars(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.organization_id == org.id,
            )
        )
        assert len(list(memberships)) == 1, "Debería haber solo 1 membresía"

        invite_db = await db.get(InviteToken, invite.id)
        assert invite_db.uses == 0, (
            "Invite no debería consumirse si no se actualiza rol"
        )

    async def test_invite_uses_incremented_correctly(
        self, db: AsyncSession, user_manager: UserManager, request_for_integration
    ):
        """The invite uses counter increments correctly."""
        org = Organization(id=uuid.uuid4(), name="Multi Use Org", slug="multi-use")
        db.add(org)
        await db.flush()

        # Invite with max_uses=3
        invite = InviteToken(
            id=uuid.uuid4(),
            token="multi-use-token",
            email=None,
            organization_id=org.id,
            role=OrgRole.MEMBER,
            is_sysadmin=False,
            max_uses=3,
            uses=0,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(invite)
        await db.commit()

        # Consume 3 times
        for i in range(3):
            user = User(
                id=uuid.uuid4(),
                email=f"user{i}@test.com",
                hashed_password="hash123",
            )
            db.add(user)
            await db.flush()

            user = await db.get(User, user.id)
            await user_manager._consume_invite_by_id(
                request_for_integration, invite.id, user
            )

        # Assertions
        invite_db = await db.get(InviteToken, invite.id)
        assert invite_db.uses == 3, "Uses debería ser 3"
        assert invite_db.is_exhausted is True, "Invite debería estar exhausto"

    async def test_sysadmin_invite_sets_superuser(
        self, db: AsyncSession, user_manager: UserManager, request_for_integration
    ):
        """Sysadmin invite makes the user a superuser."""
        user = User(
            id=uuid.uuid4(),
            email="future-admin@test.com",
            hashed_password="hash123",
            is_superuser=False,
        )
        db.add(user)
        await db.flush()

        # Sysadmin invite (no organization)
        invite = InviteToken(
            id=uuid.uuid4(),
            token="sysadmin-token",
            email=None,
            organization_id=None,
            role=None,
            is_sysadmin=True,
            max_uses=1,
            uses=0,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(invite)
        await db.commit()

        # Action: consume sysadmin invite
        user = await db.get(User, user.id)
        await user_manager._consume_invite_by_id(
            request_for_integration, invite.id, user
        )

        # Assertions
        user_db = await db.get(User, user.id)
        assert user_db.is_superuser is True, "Usuario debería ser superuser"

        invite_db = await db.get(InviteToken, invite.id)
        assert invite_db.uses == 1, "Invite debería consumirse"

    async def test_invite_with_default_member_role(
        self, db: AsyncSession, user_manager: UserManager, request_for_integration
    ):
        """Invite without a specified role uses MEMBER by default."""
        org = Organization(
            id=uuid.uuid4(), name="Default Role Org", slug="default-role"
        )
        db.add(org)
        await db.flush()

        user = User(
            id=uuid.uuid4(),
            email="default@test.com",
            hashed_password="hash123",
        )
        db.add(user)
        await db.flush()

        # Invite without role (None)
        invite = InviteToken(
            id=uuid.uuid4(),
            token="default-role-token",
            email=None,
            organization_id=org.id,
            role=None,
            is_sysadmin=False,
            max_uses=1,
            uses=0,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(invite)
        await db.commit()

        user = await db.get(User, user.id)
        await user_manager._consume_invite_by_id(
            request_for_integration, invite.id, user
        )

        # Assertions
        membership = await db.scalar(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.organization_id == org.id,
            )
        )
        assert membership.role == OrgRole.MEMBER, "Rol debería ser MEMBER por defecto"

    async def test_exhausted_invite_does_nothing(
        self, db: AsyncSession, user_manager: UserManager, request_for_integration
    ):
        """Exhausted invite does not create membership."""
        org = Organization(id=uuid.uuid4(), name="Exhausted Org", slug="exhausted")
        db.add(org)
        await db.flush()

        user = User(
            id=uuid.uuid4(),
            email="exhausted@test.com",
            hashed_password="hash123",
        )
        db.add(user)
        await db.flush()

        # Exhausted invite (uses >= max_uses)
        invite = InviteToken(
            id=uuid.uuid4(),
            token="exhausted-token",
            email=None,
            organization_id=org.id,
            role=OrgRole.MEMBER,
            is_sysadmin=False,
            max_uses=1,
            uses=1,  # Ya consumido una vez
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(invite)
        await db.commit()

        user = await db.get(User, user.id)
        await user_manager._consume_invite_by_id(
            request_for_integration, invite.id, user
        )

        # Assertions
        membership = await db.scalar(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.organization_id == org.id,
            )
        )
        assert membership is None, "No debería crear membresía si invite está exhausto"

        # Verify that uses did not change
        invite_db = await db.get(InviteToken, invite.id)
        assert invite_db.uses == 1, "Uses no debería cambiar"

    async def test_multiple_users_same_org_invite(
        self, db: AsyncSession, user_manager: UserManager, request_for_integration
    ):
        org = Organization(id=uuid.uuid4(), name="Shared Org", slug="shared")
        db.add(org)
        await db.flush()

        invite = InviteToken(
            id=uuid.uuid4(),
            token="shared-invite",
            email=None,
            organization_id=org.id,
            role=OrgRole.MEMBER,
            is_sysadmin=False,
            max_uses=2,
            uses=0,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(invite)
        await db.commit()

        users = []
        for i in range(2):
            user = User(
                id=uuid.uuid4(),
                email=f"shared-user{i}@test.com",
                hashed_password="hash123",
            )
            db.add(user)
            await db.flush()
            users.append(user)

        for user in users:
            user = await db.get(User, user.id)
            await user_manager._consume_invite_by_id(
                request_for_integration, invite.id, user
            )

        memberships = await db.scalars(
            select(Membership).where(Membership.organization_id == org.id)
        )
        memberships_list = list(memberships)
        assert len(memberships_list) == 2, "Ambos usuarios deberían estar en la org"

        invite_db = await db.get(InviteToken, invite.id)
        assert invite_db is not None, "Invite debería existir"
        assert invite_db.uses == 2, "Uses debería ser 2"
        assert invite_db.is_exhausted is True, "Invite debería estar exhausto"
