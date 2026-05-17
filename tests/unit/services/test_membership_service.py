import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.membership import MembershipService
from app.domain.entities.org_role import OrgRole


@pytest.mark.asyncio
async def test_get_admin_membership_success():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()

    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    org_repo.get.return_value = MagicMock(id=org_id)
    membership = MagicMock(user_id=user_id, organization_id=org_id, role=OrgRole.ADMIN)
    membership_repo.get_by_user_and_org.return_value = membership

    service = MembershipService(membership_repo, org_repo)
    result = await service.get_admin_membership(user_id, org_id)

    assert result is membership
    org_repo.get.assert_awaited_once_with(org_id)
    membership_repo.get_by_user_and_org.assert_awaited_once_with(user_id, org_id)


@pytest.mark.asyncio
async def test_get_admin_membership_non_admin_returns_none():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()

    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    org_repo.get.return_value = MagicMock(id=org_id)
    membership = MagicMock(user_id=user_id, organization_id=org_id, role=OrgRole.MEMBER)
    membership_repo.get_by_user_and_org.return_value = membership

    service = MembershipService(membership_repo, org_repo)
    result = await service.get_admin_membership(user_id, org_id)

    assert result is None


@pytest.mark.asyncio
async def test_get_admin_membership_org_not_found_returns_none():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()

    org_repo.get.return_value = None

    service = MembershipService(membership_repo, org_repo)
    result = await service.get_admin_membership(uuid.uuid4(), uuid.uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_is_admin_of_any():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()

    user_id = uuid.uuid4()
    membership_repo.is_admin_of_any.return_value = True

    service = MembershipService(membership_repo, org_repo)
    assert await service.is_admin_of_any(user_id) is True
    membership_repo.is_admin_of_any.assert_awaited_once_with(user_id)
