import pytest
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace

from app.auth.manager import UserManager


@pytest.fixture
def user_db_mock():
    """SQLAlchemyUserDatabase Mock"""
    return AsyncMock()


@pytest.fixture
def request_mock():
    request = MagicMock()
    request.state = SimpleNamespace()
    request.cookies = {}
    return request


@pytest.fixture
def user_manager(user_db_mock):
    manager = UserManager(user_db_mock)
    return manager
