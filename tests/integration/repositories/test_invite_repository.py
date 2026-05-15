import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.invite import InviteRepository


@pytest.mark.asyncio
async def test_create_invite(db: AsyncSession):
    repo = InviteRepository(db)
    invite = await repo.create(
        token="test-token",
        email="test@example.com",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        max_uses=1,
    )

    assert invite.id is not None
    assert invite.token == "test-token"


@pytest.mark.asyncio
async def test_get_by_token(db: AsyncSession):
    repo = InviteRepository(db)
    token = "find-me"
    await repo.create(
        token=token,
        email=None,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        max_uses=1,
    )

    found = await repo.get_by_token(token)
    assert found is not None
    assert found.token == token

    assert await repo.get_by_token("not-found") is None


@pytest.mark.asyncio
async def test_fetch_usable_invite(db: AsyncSession):
    repo = InviteRepository(db)

    # Valid invite
    await repo.create(
        token="valid",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        max_uses=1,
    )
    invite, err = await repo.fetch_usable_invite("valid")
    assert invite is not None
    assert err is None

    # Used invite
    await repo.create(
        token="used",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        max_uses=1,
        uses=1,
    )
    invite, err = await repo.fetch_usable_invite("used")
    assert invite is None
    assert err == "invite_used"

    # Expired invite
    await repo.create(
        token="expired",
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        max_uses=1,
    )
    invite, err = await repo.fetch_usable_invite("expired")
    assert invite is None
    assert err == "invite_expired"
