from types import SimpleNamespace

import pytest_asyncio
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.manager import UserManager
from app.models import OAuthAccount, User


class FakeRequest:
    """Fake Request object for testing que permite BD real."""

    def __init__(self):
        self.state = SimpleNamespace()
        self.cookies = {}


@pytest_asyncio.fixture()
async def db(db_session_maker):
    """Fixture para obtener una sesión de BD de un contexto async."""
    async with db_session_maker() as session:
        yield session


@pytest_asyncio.fixture()
async def user_manager(db: AsyncSession):
    """UserManager con UserDB real para pruebas de integración."""
    user_db = SQLAlchemyUserDatabase(db, User, OAuthAccount)
    return UserManager(user_db)


@pytest_asyncio.fixture()
async def request_for_integration(db: AsyncSession):
    """Request object para tests de integración con DB real."""
    request = FakeRequest()
    request.state.db = db
    return request
