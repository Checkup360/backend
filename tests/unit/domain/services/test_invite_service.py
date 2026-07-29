import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.entities import InviteToken
from app.domain.value_objects.org_role import OrgRole
from app.domain.exceptions import (
    InviteExhaustedError,
    InviteExpiredError,
    InviteNotFoundError,
)
from app.application.use_cases.invitations import InviteUrlBuilder
from app.domain.services import invite as invites_service
from app.infrastructure.persistence.repositories.invite import InviteRepository


def test_build_invite_token_sets_all_fields():
    organization_id = uuid.UUID("36b57de5-8fac-4dd5-a470-9e687545a363")

    invite = invites_service.build_invite_token(
        email="user@example.com",
        expires_in_hours=12,
        max_uses=3,
        organization_id=organization_id,
        role=OrgRole.ADMIN,
        is_sysadmin=True,
    )

    assert invite.token
    assert invite.email == "user@example.com"
    assert invite.max_uses == 3
    assert invite.organization_id == organization_id
    assert invite.role == OrgRole.ADMIN
    assert invite.is_sysadmin is True
    assert invite.expires_at.tzinfo is not None


def test_build_invite_url_uses_frontend_url():
    builder = InviteUrlBuilder("https://app.example.com/")
    assert builder.build("abc123") == "https://app.example.com/invite/abc123"


@pytest.mark.asyncio
async def test_check_invite_usable_not_found():
    repo = AsyncMock(spec=InviteRepository)
    repo.get_by_token.return_value = None
    service = invites_service.InviteService(repo, AsyncMock(), AsyncMock())

    with pytest.raises(InviteNotFoundError):
        await service.check_invite_usable("no-such-token")


@pytest.mark.asyncio
async def test_check_invite_usable_used():
    repo = AsyncMock(spec=InviteRepository)
    token = InviteToken(
        id=uuid.uuid4(),
        token="used-token",
        uses=1,
        max_uses=1,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    repo.get_by_token.return_value = token
    service = invites_service.InviteService(repo, AsyncMock(), AsyncMock())

    with pytest.raises(InviteExhaustedError):
        await service.check_invite_usable("used-token")


@pytest.mark.asyncio
async def test_check_invite_usable_expired():
    repo = AsyncMock(spec=InviteRepository)
    token = InviteToken(
        id=uuid.uuid4(),
        token="expired-token",
        uses=0,
        max_uses=1,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    repo.get_by_token.return_value = token
    service = invites_service.InviteService(repo, AsyncMock(), AsyncMock())

    with pytest.raises(InviteExpiredError):
        await service.check_invite_usable("expired-token")


@pytest.mark.asyncio
async def test_check_invite_usable_valid():
    repo = AsyncMock(spec=InviteRepository)
    token = InviteToken(
        id=uuid.uuid4(),
        token="valid-token",
        uses=0,
        max_uses=1,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    repo.get_by_token.return_value = token
    service = invites_service.InviteService(repo, AsyncMock(), AsyncMock())

    await service.check_invite_usable("valid-token")


@pytest.mark.asyncio
async def test_check_invite_usable_edge_expiry_just_now():
    repo = AsyncMock(spec=InviteRepository)
    token = InviteToken(
        id=uuid.uuid4(),
        token="edge-token",
        uses=0,
        max_uses=1,
        expires_at=datetime.now(timezone.utc),
    )
    repo.get_by_token.return_value = token
    service = invites_service.InviteService(repo, AsyncMock(), AsyncMock())

    with pytest.raises(InviteExpiredError):
        await service.check_invite_usable("edge-token")


@pytest.mark.asyncio
async def test_consume_invite_copies_department_id_to_membership():
    invite_repo = AsyncMock()
    membership_repo = AsyncMock()
    user_repo = AsyncMock()
    invite_id = uuid.uuid4()
    user_id = uuid.uuid4()
    organization_id = uuid.uuid4()
    department_id = uuid.uuid4()
    invite_repo.get.return_value = InviteToken(
        id=invite_id,
        token="department-token",
        uses=0,
        max_uses=1,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        organization_id=organization_id,
        department_id=department_id,
        role=OrgRole.MEMBER,
    )
    user_repo.get.return_value = type("User", (), {"id": user_id})()
    membership_repo.get_by_user_and_org.return_value = None

    service = invites_service.InviteService(invite_repo, membership_repo, user_repo)
    await service.consume_invite(invite_id, user_id)

    saved = membership_repo.save.call_args.args[0]
    assert saved.department_id == department_id


@pytest.mark.asyncio
async def test_check_invite_usable_expired_naive_datetime():
    repo = AsyncMock(spec=InviteRepository)
    token = InviteToken(
        id=uuid.uuid4(),
        token="expired-naive-token",
        uses=0,
        max_uses=1,
        expires_at=datetime.now() - timedelta(hours=2),  # naive datetime in past
    )
    repo.get_by_token.return_value = token
    service = invites_service.InviteService(repo, AsyncMock(), AsyncMock())

    with pytest.raises(InviteExpiredError):
        await service.check_invite_usable("expired-naive-token")


@pytest.mark.asyncio
async def test_validate_invite_raises_expired():
    repo = AsyncMock(spec=InviteRepository)
    token = InviteToken(
        id=uuid.uuid4(),
        token="expired-token",
        email="user@example.com",
        uses=0,
        max_uses=1,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    repo.get_by_token.return_value = token
    service = invites_service.InviteService(repo, AsyncMock(), AsyncMock())

    with pytest.raises(InviteExpiredError):
        await service.validate_invite("expired-token", "user@example.com")


@pytest.mark.asyncio
async def test_validate_invite_email_mismatch_raises():
    from app.domain.exceptions import InviteEmailMismatchError

    repo = AsyncMock(spec=InviteRepository)
    token = InviteToken(
        id=uuid.uuid4(),
        token="valid-token",
        email="owner@example.com",
        uses=0,
        max_uses=1,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    repo.get_by_token.return_value = token
    service = invites_service.InviteService(repo, AsyncMock(), AsyncMock())

    with pytest.raises(InviteEmailMismatchError):
        await service.validate_invite("valid-token", "imposter@example.com")


@pytest.mark.asyncio
async def test_validate_invite_success():
    repo = AsyncMock(spec=InviteRepository)
    token = InviteToken(
        id=uuid.uuid4(),
        token="valid-token",
        email="owner@example.com",
        uses=0,
        max_uses=1,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    repo.get_by_token.return_value = token
    service = invites_service.InviteService(repo, AsyncMock(), AsyncMock())
    result = await service.validate_invite("valid-token", "owner@example.com")
    assert result == token


# --- Create Invite Tests ---


@pytest.mark.asyncio
async def test_create_invite_with_dept_missing_org_raises_error():
    from app.domain.exceptions import InviteDepartmentNotFoundError

    dept_repo = AsyncMock()
    service = invites_service.InviteService(
        AsyncMock(), AsyncMock(), AsyncMock(), department_repo=dept_repo
    )

    with pytest.raises(InviteDepartmentNotFoundError):
        await service.create_invite(
            email="user@example.com",
            expires_in_hours=24,
            max_uses=1,
            organization_id=None,
            department_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_create_invite_with_non_existent_dept_raises_error():
    from app.domain.exceptions import InviteDepartmentNotFoundError

    dept_repo = AsyncMock()
    dept_repo.get_by_organization.return_value = None
    service = invites_service.InviteService(
        AsyncMock(), AsyncMock(), AsyncMock(), department_repo=dept_repo
    )

    with pytest.raises(InviteDepartmentNotFoundError):
        await service.create_invite(
            email="user@example.com",
            expires_in_hours=24,
            max_uses=1,
            organization_id=uuid.uuid4(),
            department_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_create_invite_success():
    invite_repo = AsyncMock()
    dept_repo = AsyncMock()
    dept_repo.get_by_organization.return_value = MagicMock()
    created_token = MagicMock()
    invite_repo.save.return_value = created_token

    org_id = uuid.uuid4()
    dept_id = uuid.uuid4()

    service = invites_service.InviteService(
        invite_repo, AsyncMock(), AsyncMock(), department_repo=dept_repo
    )
    result = await service.create_invite(
        email="user@example.com",
        expires_in_hours=24,
        max_uses=1,
        organization_id=org_id,
        department_id=dept_id,
        role=OrgRole.MEMBER,
    )

    assert result == created_token
    invite_repo.save.assert_awaited_once()


# --- Consume Invite Tests ---


@pytest.mark.asyncio
async def test_consume_invite_not_found_raises():
    invite_repo = AsyncMock()
    invite_repo.get.return_value = None
    service = invites_service.InviteService(invite_repo, AsyncMock(), AsyncMock())

    with pytest.raises(InviteNotFoundError):
        await service.consume_invite(uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_consume_invite_exhausted_raises():
    invite_repo = AsyncMock()
    invite_repo.get.return_value = InviteToken(
        id=uuid.uuid4(),
        token="tok",
        uses=1,
        max_uses=1,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    service = invites_service.InviteService(invite_repo, AsyncMock(), AsyncMock())

    with pytest.raises(InviteExhaustedError):
        await service.consume_invite(uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_consume_invite_user_not_found_raises():
    from app.domain.exceptions import UserNotFoundError

    invite_repo = AsyncMock()
    user_repo = AsyncMock()
    invite_repo.get.return_value = InviteToken(
        id=uuid.uuid4(),
        token="tok",
        uses=0,
        max_uses=1,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    user_repo.get.return_value = None
    service = invites_service.InviteService(invite_repo, AsyncMock(), user_repo)

    with pytest.raises(UserNotFoundError):
        await service.consume_invite(uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_consume_invite_sysadmin_updates_user():
    invite_repo = AsyncMock()
    user_repo = AsyncMock()
    invite_id = uuid.uuid4()
    user_id = uuid.uuid4()

    invite_repo.get.return_value = InviteToken(
        id=invite_id,
        token="sysadmin-tok",
        uses=0,
        max_uses=1,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        is_sysadmin=True,
    )
    user_repo.get.return_value = MagicMock(id=user_id)

    service = invites_service.InviteService(invite_repo, AsyncMock(), user_repo)
    await service.consume_invite(invite_id, user_id)

    user_repo.update.assert_awaited_once_with(user_id, is_superuser=True)
    invite_repo.update.assert_awaited_once_with(invite_id, uses=1)


@pytest.mark.asyncio
async def test_consume_invite_updates_existing_membership_roles_and_dept():
    invite_repo = AsyncMock()
    membership_repo = AsyncMock()
    user_repo = AsyncMock()

    invite_id = uuid.uuid4()
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    dept_id = uuid.uuid4()

    invite_repo.get.return_value = InviteToken(
        id=invite_id,
        token="role-tok",
        uses=0,
        max_uses=1,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        organization_id=org_id,
        department_id=dept_id,
        role=OrgRole.ADMIN,
    )
    user_repo.get.return_value = MagicMock(id=user_id)
    existing_membership = MagicMock(roles=[OrgRole.MEMBER], department_id=None)
    membership_repo.get_by_user_and_org.return_value = existing_membership

    service = invites_service.InviteService(invite_repo, membership_repo, user_repo)
    await service.consume_invite(invite_id, user_id)

    assert OrgRole.ADMIN in existing_membership.roles
    assert existing_membership.department_id == dept_id
    membership_repo.save.assert_awaited_once_with(existing_membership)
    invite_repo.update.assert_awaited_once_with(invite_id, uses=1)
