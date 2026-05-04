import uuid

import pytest

from app.invites import service as invites_service
from app.models.membership import OrgRole


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
async def test_fetch_usable_invite_edge_expiry_just_now(mock_db, make_invite_token):
    """Test invite that expires exactly now (should be expired)."""
    token = make_invite_token(token="edge-token", expires_in_hours=0)
    mock_db.scalar.return_value = token

    invite, code = await invites_service.fetch_usable_invite(mock_db, "edge-token")

    assert invite is None
    assert code == "invite_expired"
