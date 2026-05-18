import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.domain.entities import InviteToken
from app.domain.entities.org_role import OrgRole
from app.services import invite as invites_service
from app.repositories.invite import InviteRepository


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
    assert invites_service.build_invite_url("abc123").endswith("/invite/abc123")


@pytest.mark.asyncio
async def test_check_invite_usable_not_found():
    repo = AsyncMock(spec=InviteRepository)
    repo.get_by_token.return_value = None
    service = invites_service.InviteService(repo, AsyncMock(), AsyncMock())

    err = await service.check_invite_usable("no-such-token")

    assert err == "invalid_invite"


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

    err = await service.check_invite_usable("used-token")

    assert err == "invite_used"


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

    err = await service.check_invite_usable("expired-token")

    assert err == "invite_expired"


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

    err = await service.check_invite_usable("valid-token")

    assert err is None


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

    err = await service.check_invite_usable("edge-token")

    assert err == "invite_expired"
