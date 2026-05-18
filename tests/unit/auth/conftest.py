import pytest
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace
import uuid
from datetime import datetime, timezone

from app.auth.manager import UserManager
from app.domain.entities import InviteToken, Membership, User
from app.domain.entities.org_role import OrgRole
from app.services.invite import InviteService


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
def invite_repo_mock():
    return AsyncMock()


@pytest.fixture
def membership_repo_mock():
    return AsyncMock()


@pytest.fixture
def user_repo_mock():
    return AsyncMock()


@pytest.fixture
def invite_service_mock(invite_repo_mock, membership_repo_mock, user_repo_mock):
    return InviteService(invite_repo_mock, membership_repo_mock, user_repo_mock)


@pytest.fixture
def user_manager(user_db_mock, invite_service_mock):
    manager = UserManager(user_db_mock, invite_service_mock)
    return manager


@pytest.fixture
def sample_user():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "user@example.com"
    user.is_superuser = False
    return user


@pytest.fixture
def sample_invite_org():
    return InviteToken(
        id=uuid.uuid4(),
        token="test-invite-token",
        email=None,
        organization_id=uuid.uuid4(),
        role=OrgRole.MEMBER,
        is_sysadmin=False,
        uses=0,
        max_uses=1,
        expires_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_invite_sysadmin():
    return InviteToken(
        id=uuid.uuid4(),
        token="test-sysadmin-invite",
        email=None,
        organization_id=None,
        role=None,
        is_sysadmin=True,
        uses=0,
        max_uses=1,
        expires_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_membership():
    return Membership(
        user_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        role=OrgRole.ADMIN,
    )
