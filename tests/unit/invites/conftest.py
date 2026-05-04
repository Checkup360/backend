import pytest
from datetime import datetime, timedelta, timezone

from app.models.invite import InviteToken


@pytest.fixture
def make_invite_token():
    def _make_invite(
        token: str = "test-token",
        email: str = "test@example.com",
        used: bool = False,
        expires_in_hours: int = 1,
    ) -> InviteToken:
        invite = InviteToken()
        invite.token = token
        invite.email = email
        invite.uses = 1 if used else 0
        invite.max_uses = 1
        invite.expires_at = datetime.now(timezone.utc) + timedelta(
            hours=expires_in_hours
        )
        return invite

    return _make_invite
