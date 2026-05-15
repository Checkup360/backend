import pytest
from datetime import datetime, timedelta, timezone
from app.models.invite import InviteToken


@pytest.fixture
def make_invite_token():
    """Helper to create InviteToken objects for tests."""

    def _make(
        token="some-token",
        used=False,
        expires_in_hours=1,
    ):
        return InviteToken(
            token=token,
            uses=1 if used else 0,
            max_uses=1,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
        )

    return _make
