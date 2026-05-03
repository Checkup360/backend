from datetime import datetime, timedelta, timezone

import pytest

from app.auth.users import current_active_user
from app.main import app
from app.models import InviteToken


@pytest.fixture()
def override_current_user():
    def _override(user):
        app.dependency_overrides[current_active_user] = lambda: user

    yield _override
    app.dependency_overrides.clear()


@pytest.fixture()
def make_invite(db_session_maker):
    async def _make_invite(
        token: str = "test-token",
        email: str = "test@example.com",
        used: bool = False,
        expires_in_hours: int = 1,
    ) -> InviteToken:
        invite = InviteToken()
        invite.token = token
        invite.email = email
        invite.used = used
        invite.expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

        async with db_session_maker() as session:
            session.add(invite)
            await session.commit()

        return invite

    return _make_invite
