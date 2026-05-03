import pytest
from datetime import datetime, timedelta, timezone

from app.invites import service as invites_service


@pytest.mark.asyncio
async def test_fetch_usable_invite_not_found(mock_db):
    mock_db.scalar.return_value = None

    invite, code = await invites_service.fetch_usable_invite(mock_db, "no-such-token")

    assert invite is None
    assert code == "invalid_invite"


@pytest.mark.asyncio
async def test_fetch_usable_invite_used(mock_db, make_invite_token):
    token = make_invite_token(token="used-token", used=True)
    mock_db.scalar.return_value = token

    invite, code = await invites_service.fetch_usable_invite(mock_db, "used-token")

    assert invite is None
    assert code == "invite_used"


@pytest.mark.asyncio
async def test_fetch_usable_invite_expired(mock_db, make_invite_token):
    token = make_invite_token(token="expired-token", expires_in_hours=-1)
    mock_db.scalar.return_value = token

    invite, code = await invites_service.fetch_usable_invite(mock_db, "expired-token")

    assert invite is None
    assert code == "invite_expired"


@pytest.mark.asyncio
async def test_fetch_usable_invite_valid(mock_db, make_invite_token):
    token = make_invite_token(token="valid-token")
    mock_db.scalar.return_value = token

    invite, code = await invites_service.fetch_usable_invite(mock_db, "valid-token")

    assert invite is token
    assert code is None


@pytest.mark.asyncio
async def test_fetch_usable_invite_edge_expiry_just_now(mock_db):
    """Test invite that expires exactly now (should be expired)."""
    now_utc = datetime.now(timezone.utc)
    token = mock_db.scalar.return_value = type('Token', (), {
        'token': 'edge-token',
        'used': False,
        'expires_at': now_utc
    })()

    invite, code = await invites_service.fetch_usable_invite(mock_db, "edge-token")

    assert invite is None
    assert code == "invite_expired"
