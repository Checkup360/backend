from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.users import current_active_user
from app.auth.manager import UserManager
from app.main import app
from app.models import InviteToken


class FakeRequest:
    """Fake Request object for testing que permite BD real."""

    def __init__(self):
        self.state = SimpleNamespace()
        self.cookies = {}


@pytest.fixture()
def override_current_user():
    def _override(user):
        app.dependency_overrides[current_active_user] = lambda: user

    yield _override
    app.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def db(db_session_maker):
    """Fixture para obtener una sesión de BD de un contexto async."""
    async with db_session_maker() as session:
        yield session


@pytest.fixture()
def user_db_mock():
    """Mock de SQLAlchemyUserDatabase."""
    return AsyncMock()


@pytest.fixture()
def user_manager(user_db_mock):
    """Manager de usuarios para tests."""
    return UserManager(user_db_mock)


@pytest_asyncio.fixture()
async def request_for_integration(db: AsyncSession):
    """Request object para tests de integración con DB real."""
    request = FakeRequest()
    request.state.db = db
    return request


@pytest.fixture()
def request_mock():
    """Mock de FastAPI Request para tests unitarios."""
    request = MagicMock()
    request.state = SimpleNamespace()
    request.cookies = {}
    return request


@pytest_asyncio.fixture()
async def make_invite(db_session_maker):
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
        invite.expires_at = datetime.now(timezone.utc) + timedelta(
            hours=expires_in_hours
        )

        async with db_session_maker() as session:
            session.add(invite)
            await session.commit()

        return invite

    return _make_invite
