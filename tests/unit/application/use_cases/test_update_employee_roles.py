import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.application.use_cases.memberships.update_employee_roles import (
    UpdateEmployeeRolesUseCase,
)
from app.domain.exceptions import (
    InsufficientRolePermissionError,
    NotOrganizationAdminError,
    SuperadminDirectRemovalForbiddenError,
)
from app.domain.value_objects import OrgRole


@pytest.mark.asyncio
async def test_update_roles_not_admin_raises():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()
    refresh_token_repo = AsyncMock()

    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    target_id = uuid.uuid4()

    org_repo.get.return_value = MagicMock(id=org_id)
    membership_repo.get_by_user_and_org.side_effect = [
        MagicMock(user_id=target_id, roles=[OrgRole.MEMBER]),
        MagicMock(user_id=actor_id, roles=[OrgRole.MEMBER]),
    ]

    use_case = UpdateEmployeeRolesUseCase(membership_repo, org_repo, refresh_token_repo)

    with pytest.raises(NotOrganizationAdminError):
        await use_case.execute(
            actor_user_id=actor_id,
            actor_is_superuser=False,
            organization_id=org_id,
            target_user_id=target_id,
            new_roles=[OrgRole.CONTENT_MANAGER],
        )


@pytest.mark.asyncio
async def test_regular_admin_cannot_modify_admin():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()
    refresh_token_repo = AsyncMock()

    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    target_id = uuid.uuid4()

    org_repo.get.return_value = MagicMock(id=org_id)
    membership_repo.get_by_user_and_org.side_effect = [
        MagicMock(user_id=target_id, roles=[OrgRole.ADMIN]),
        MagicMock(user_id=actor_id, roles=[OrgRole.ADMIN]),
    ]

    use_case = UpdateEmployeeRolesUseCase(membership_repo, org_repo, refresh_token_repo)

    with pytest.raises(InsufficientRolePermissionError):
        await use_case.execute(
            actor_user_id=actor_id,
            actor_is_superuser=False,
            organization_id=org_id,
            target_user_id=target_id,
            new_roles=[OrgRole.MEMBER],
        )


@pytest.mark.asyncio
async def test_superadmin_cannot_directly_remove_superadmin():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()
    refresh_token_repo = AsyncMock()

    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    target_id = uuid.uuid4()

    org_repo.get.return_value = MagicMock(id=org_id)
    membership_repo.get_by_user_and_org.side_effect = [
        MagicMock(user_id=target_id, roles=[OrgRole.SUPERADMIN]),
        MagicMock(user_id=actor_id, roles=[OrgRole.SUPERADMIN]),
    ]

    use_case = UpdateEmployeeRolesUseCase(membership_repo, org_repo, refresh_token_repo)

    with pytest.raises(SuperadminDirectRemovalForbiddenError):
        await use_case.execute(
            actor_user_id=actor_id,
            actor_is_superuser=False,
            organization_id=org_id,
            target_user_id=target_id,
            new_roles=[OrgRole.ADMIN],
        )


@pytest.mark.asyncio
async def test_update_roles_revokes_tokens_when_losing_member():
    membership_repo = AsyncMock()
    org_repo = AsyncMock()
    refresh_token_repo = AsyncMock()

    org_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    target_id = uuid.uuid4()

    org_repo.get.return_value = MagicMock(id=org_id)
    target_membership = MagicMock(user_id=target_id, roles=[OrgRole.MEMBER])
    actor_membership = MagicMock(user_id=actor_id, roles=[OrgRole.ADMIN])
    membership_repo.get_by_user_and_org.side_effect = [
        target_membership,
        actor_membership,
    ]
    expected_employee = MagicMock(user=MagicMock(id=target_id))
    membership_repo.get_employee.return_value = expected_employee

    use_case = UpdateEmployeeRolesUseCase(membership_repo, org_repo, refresh_token_repo)

    result = await use_case.execute(
        actor_user_id=actor_id,
        actor_is_superuser=False,
        organization_id=org_id,
        target_user_id=target_id,
        new_roles=[OrgRole.CONTENT_MANAGER],
    )

    assert result is expected_employee
    refresh_token_repo.revoke_all_for_user.assert_awaited_once_with(target_id)
    membership_repo.save.assert_awaited_once_with(target_membership)
