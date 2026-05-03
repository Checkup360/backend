import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from app.invites import service as invites_service
from app.models.invite import InviteToken


@pytest.mark.asyncio
async def test_fetch_usable_invite_not_found():
    db = AsyncMock()
    db.scalar = AsyncMock(return_value=None)

    invite, code = await invites_service.fetch_usable_invite(db, "no-such-token")

    assert invite is None
    assert code == "invalid_invite"


@pytest.mark.asyncio
async def test_fetch_usable_invite_used():
    token = InviteToken()
    token.token = "used-token"
    token.used = True
    token.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    db = AsyncMock()
    db.scalar = AsyncMock(return_value=token)

    invite, code = await invites_service.fetch_usable_invite(db, "used-token")

    assert invite is None
    assert code == "invite_used"


@pytest.mark.asyncio
async def test_fetch_usable_invite_expired():
    token = InviteToken()
    token.token = "expired-token"
    token.used = False
    token.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    db = AsyncMock()
    db.scalar = AsyncMock(return_value=token)

    invite, code = await invites_service.fetch_usable_invite(db, "expired-token")

    assert invite is None
    assert code == "invite_expired"


@pytest.mark.asyncio
async def test_fetch_usable_invite_valid():
    token = InviteToken()
    token.token = "valid-token"
    token.used = False
    token.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    db = AsyncMock()
    db.scalar = AsyncMock(return_value=token)

    invite, code = await invites_service.fetch_usable_invite(db, "valid-token")

    assert invite is token
    assert code is None
