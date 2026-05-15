import pytest
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace
import uuid
from datetime import datetime, timezone

from app.auth.manager import UserManager
from app.services.invite import InviteService
from app.models.membership import OrgRole


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
    """Create a sample user object for testing."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "user@example.com"
    user.is_superuser = False
    return user


@pytest.fixture
def sample_invite_org():
    """Create a sample invite for organization with role."""
    invite = MagicMock()
    invite.id = uuid.uuid4()
    invite.token = "test-invite-token"
    invite.email = None
    invite.organization_id = uuid.uuid4()
    invite.role = OrgRole.MEMBER
    invite.is_sysadmin = False
    invite.is_exhausted = False
    invite.uses = 0
    invite.max_uses = 1
    invite.expires_at = datetime.now(timezone.utc)
    return invite


@pytest.fixture
def sample_invite_sysadmin():
    """Create a sample invite for sysadmin."""
    invite = MagicMock()
    invite.id = uuid.uuid4()
    invite.token = "test-sysadmin-invite"
    invite.email = None
    invite.organization_id = None
    invite.role = None
    invite.is_sysadmin = True
    invite.is_exhausted = False
    invite.uses = 0
    invite.max_uses = 1
    invite.expires_at = datetime.now(timezone.utc)
    return invite


@pytest.fixture
def sample_membership():
    """Create a sample membership object."""
    membership = MagicMock()
    membership.user_id = uuid.uuid4()
    membership.organization_id = uuid.uuid4()
    membership.role = OrgRole.ADMIN
    return membership
