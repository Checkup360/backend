from types import SimpleNamespace

import pytest_asyncio
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.authentication.manager import UserManager
from app.infrastructure.persistence.models import OAuthAccount, User
from app.infrastructure.persistence.repositories.invite import InviteRepository
from app.infrastructure.persistence.repositories.membership import MembershipRepository
from app.infrastructure.persistence.repositories.user import UserRepository
from app.domain.services.invite import InviteService


class FakeRequest:
    """Fake Request object for testing que permite BD real."""

    def __init__(self):
        self.state = SimpleNamespace()
        self.cookies = {}


@pytest_asyncio.fixture()
async def user_manager(db: AsyncSession):
    """UserManager con UserDB real para pruebas de integración."""
    user_db = SQLAlchemyUserDatabase(db, User, OAuthAccount)
    invite_repo = InviteRepository(db)
    membership_repo = MembershipRepository(db)
    user_repo = UserRepository(db)
    invite_service = InviteService(invite_repo, membership_repo, user_repo)
    return UserManager(user_db, invite_service)


@pytest_asyncio.fixture()
async def request_for_integration(db: AsyncSession):
    """Request object para tests de integración con DB real."""
    request = FakeRequest()
    request.state.db = db
    return request
