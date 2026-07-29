import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.application.use_cases.memberships.membership_service import MembershipService
from app.domain.value_objects.org_role import OrgRole
from app.domain.exceptions import (
    NotOrganizationAdminError,
    OrganizationNotFoundError,
)


@pytest.mark.asyncio
async def test_get_admin_membership_success():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()

    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    org_repo.get.return_value = MagicMock(id=org_id)
    membership = MagicMock(
        user_id=user_id, organization_id=org_id, roles=[OrgRole.ADMIN]
    )
    membership_repo.get_by_user_and_org.return_value = membership

    service = MembershipService(membership_repo, org_repo)
    result = await service.get_admin_membership(user_id, org_id)

    assert result is membership
    org_repo.get.assert_awaited_once_with(org_id)
    membership_repo.get_by_user_and_org.assert_awaited_once_with(user_id, org_id)


@pytest.mark.asyncio
async def test_get_admin_membership_non_admin_raises():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()

    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    org_repo.get.return_value = MagicMock(id=org_id)
    membership = MagicMock(
        user_id=user_id, organization_id=org_id, roles=[OrgRole.MEMBER]
    )
    membership_repo.get_by_user_and_org.return_value = membership

    service = MembershipService(membership_repo, org_repo)

    with pytest.raises(NotOrganizationAdminError):
        await service.get_admin_membership(user_id, org_id)


@pytest.mark.asyncio
async def test_get_admin_membership_org_not_found_raises():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()

    org_repo.get.return_value = None

    service = MembershipService(membership_repo, org_repo)

    with pytest.raises(OrganizationNotFoundError):
        await service.get_admin_membership(uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_is_admin_of_any():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()

    user_id = uuid.uuid4()
    membership_repo.is_admin_of_any.return_value = True

    service = MembershipService(membership_repo, org_repo)
    assert await service.is_admin_of_any(user_id) is True
    membership_repo.is_admin_of_any.assert_awaited_once_with(user_id)


@pytest.mark.asyncio
async def test_list_employees_for_organization_admin_returns_filtered_roles():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()

    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    employees = [MagicMock()]
    org_repo.get.return_value = MagicMock(id=org_id)
    membership_repo.get_by_user_and_org.return_value = MagicMock(
        user_id=user_id, organization_id=org_id, roles=[OrgRole.ADMIN]
    )
    membership_repo.list_members_for_organization.return_value = employees

    service = MembershipService(membership_repo, org_repo)
    result = await service.list_employees_for_organization_admin(
        user_id, org_id, roles=[OrgRole.MEMBER]
    )

    assert result == employees
    membership_repo.get_by_user_and_org.assert_awaited_once_with(user_id, org_id)
    membership_repo.list_members_for_organization.assert_awaited_once_with(
        org_id, roles=[OrgRole.MEMBER]
    )


@pytest.mark.asyncio
async def test_list_employees_for_organization_admin_without_role_filter():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()

    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    org_repo.get.return_value = MagicMock(id=org_id)
    membership_repo.get_by_user_and_org.return_value = MagicMock(
        user_id=user_id, organization_id=org_id, roles=[OrgRole.ADMIN]
    )
    membership_repo.list_members_for_organization.return_value = []

    service = MembershipService(membership_repo, org_repo)
    await service.list_employees_for_organization_admin(user_id, org_id)

    membership_repo.list_members_for_organization.assert_awaited_once_with(
        org_id, roles=None
    )


@pytest.mark.asyncio
async def test_list_employees_for_organization_admin_without_admin_membership_raises():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()

    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    org_repo.get.return_value = MagicMock(id=org_id)
    membership_repo.get_by_user_and_org.return_value = None

    service = MembershipService(membership_repo, org_repo)

    with pytest.raises(NotOrganizationAdminError):
        await service.list_employees_for_organization_admin(user_id, org_id)
    membership_repo.list_members_for_organization.assert_not_awaited()


@pytest.mark.asyncio
async def test_count_employees_for_organization_admin_returns_filtered_count():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()

    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    org_repo.get.return_value = MagicMock(id=org_id)
    membership_repo.get_by_user_and_org.return_value = MagicMock(
        user_id=user_id, organization_id=org_id, roles=[OrgRole.ADMIN]
    )
    membership_repo.count_members_for_organization.return_value = 3

    service = MembershipService(membership_repo, org_repo)
    result = await service.count_employees_for_organization_admin(
        user_id, org_id, roles=[OrgRole.MEMBER]
    )

    assert result == 3
    membership_repo.get_by_user_and_org.assert_awaited_once_with(user_id, org_id)
    membership_repo.count_members_for_organization.assert_awaited_once_with(
        org_id, roles=[OrgRole.MEMBER]
    )


@pytest.mark.asyncio
async def test_count_employees_for_organization_admin_without_admin_membership_raises():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()

    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    org_repo.get.return_value = MagicMock(id=org_id)
    membership_repo.get_by_user_and_org.return_value = None

    service = MembershipService(membership_repo, org_repo)

    with pytest.raises(NotOrganizationAdminError):
        await service.count_employees_for_organization_admin(user_id, org_id)
    membership_repo.count_members_for_organization.assert_not_awaited()


@pytest.mark.asyncio
async def test_count_members_for_organization_direct_call():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()
    org_id = uuid.uuid4()
    membership_repo.count_members_for_organization.return_value = 12

    service = MembershipService(membership_repo, org_repo)
    result = await service.count_members_for_organization(
        org_id, roles=[OrgRole.MEMBER]
    )

    assert result == 12
    membership_repo.count_members_for_organization.assert_awaited_once_with(
        org_id, roles=[OrgRole.MEMBER]
    )
