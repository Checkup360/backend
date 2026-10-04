import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.use_cases.memberships.update_employee_roles import (
    SUPERADMIN_ROLE_GRANTED,
    SUPERADMIN_ROLE_REMOVED,
    UpdateEmployeeRolesUseCase,
)
from app.domain.entities.membership import Membership
from app.domain.exceptions import (
    CannotRemoveLastSuperadminError,
    CannotRemoveOwnSuperadminError,
    InsufficientRolePermissionError,
    NotOrganizationAdminError,
)
from app.domain.value_objects import OrgRole

ORG_ID = uuid.uuid4()
ACTOR_ID = uuid.uuid4()
TARGET_ID = uuid.uuid4()


def _membership(user_id: uuid.UUID, roles: list[OrgRole]) -> Membership:
    return Membership(user_id=user_id, organization_id=ORG_ID, roles=list(roles))


def _build(
    target_roles: list[OrgRole],
    actor_roles: list[OrgRole] | None = None,
    superadmin_count: int = 2,
    target_id: uuid.UUID = TARGET_ID,
):
    membership_repo = AsyncMock()
    memberships = {target_id: _membership(target_id, target_roles)}
    if actor_roles is not None:
        memberships.setdefault(ACTOR_ID, _membership(ACTOR_ID, actor_roles))
    membership_repo.get_by_user_and_org.side_effect = lambda user_id, _org: (
        memberships.get(user_id)
    )
    membership_repo.count_superadmins.return_value = superadmin_count
    membership_repo.get_employee.return_value = MagicMock()
    org_repo = AsyncMock()
    org_repo.get.return_value = MagicMock(id=ORG_ID)
    refresh_token_repo = AsyncMock()
    audit_log_repo = AsyncMock()
    use_case = UpdateEmployeeRolesUseCase(
        membership_repo, org_repo, refresh_token_repo, audit_log_repo
    )
    return use_case, membership_repo, refresh_token_repo, audit_log_repo


async def _execute(use_case, new_roles, *, superuser=False, target_id=TARGET_ID):
    return await use_case.execute(
        actor_user_id=ACTOR_ID,
        actor_is_superuser=superuser,
        organization_id=ORG_ID,
        target_user_id=target_id,
        new_roles=new_roles,
    )


@pytest.mark.asyncio
async def test_member_cannot_change_roles():
    use_case, *_ = _build([OrgRole.MEMBER], actor_roles=[OrgRole.MEMBER])

    with pytest.raises(NotOrganizationAdminError):
        await _execute(use_case, [OrgRole.CONTENT_MANAGER])


@pytest.mark.asyncio
async def test_regular_admin_cannot_modify_admin():
    use_case, *_ = _build([OrgRole.ADMIN], actor_roles=[OrgRole.ADMIN])

    with pytest.raises(InsufficientRolePermissionError):
        await _execute(use_case, [OrgRole.MEMBER])


@pytest.mark.asyncio
async def test_regular_admin_cannot_grant_superadmin():
    use_case, *_ = _build([OrgRole.MEMBER], actor_roles=[OrgRole.ADMIN])

    with pytest.raises(InsufficientRolePermissionError):
        await _execute(use_case, [OrgRole.SUPERADMIN, OrgRole.ADMIN])


@pytest.mark.asyncio
async def test_regular_admin_cannot_remove_superadmin():
    use_case, membership_repo, *_ = _build(
        [OrgRole.SUPERADMIN, OrgRole.ADMIN], actor_roles=[OrgRole.ADMIN]
    )

    with pytest.raises(InsufficientRolePermissionError):
        await _execute(use_case, [OrgRole.ADMIN])
    membership_repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_superadmin_removes_another_superadmin_and_it_is_audited():
    use_case, membership_repo, _, audit_log_repo = _build(
        [OrgRole.SUPERADMIN, OrgRole.ADMIN],
        actor_roles=[OrgRole.SUPERADMIN, OrgRole.ADMIN],
        superadmin_count=2,
    )

    await _execute(use_case, [OrgRole.ADMIN])

    saved = membership_repo.save.call_args.args[0]
    assert saved.roles == [OrgRole.ADMIN]
    entry = audit_log_repo.log.call_args.args[0]
    assert entry.action == SUPERADMIN_ROLE_REMOVED
    assert entry.user_id == ACTOR_ID
    assert entry.resource_id == str(TARGET_ID)
    assert entry.organization_id == ORG_ID


@pytest.mark.asyncio
async def test_superadmin_deactivating_another_superadmin_revokes_sessions():
    use_case, _, refresh_token_repo, audit_log_repo = _build(
        [OrgRole.SUPERADMIN, OrgRole.ADMIN, OrgRole.MEMBER],
        actor_roles=[OrgRole.SUPERADMIN, OrgRole.ADMIN],
        superadmin_count=3,
    )

    await _execute(use_case, [])

    refresh_token_repo.revoke_all_for_user.assert_awaited_once_with(TARGET_ID)
    assert audit_log_repo.log.call_args.args[0].action == SUPERADMIN_ROLE_REMOVED


@pytest.mark.asyncio
@pytest.mark.parametrize("new_roles", [[OrgRole.ADMIN], []])
async def test_superadmin_cannot_remove_own_superadmin_role(new_roles):
    use_case, membership_repo, _, audit_log_repo = _build(
        [OrgRole.SUPERADMIN, OrgRole.ADMIN], superadmin_count=3, target_id=ACTOR_ID
    )

    with pytest.raises(CannotRemoveOwnSuperadminError):
        await _execute(use_case, new_roles, target_id=ACTOR_ID)
    membership_repo.save.assert_not_called()
    audit_log_repo.log.assert_not_called()


@pytest.mark.asyncio
async def test_last_superadmin_cannot_be_removed_even_by_sysadmin():
    use_case, membership_repo, *_ = _build(
        [OrgRole.SUPERADMIN, OrgRole.ADMIN], superadmin_count=1
    )

    with pytest.raises(CannotRemoveLastSuperadminError):
        await _execute(use_case, [OrgRole.ADMIN], superuser=True)
    membership_repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_sysadmin_can_remove_a_superadmin_when_another_remains():
    use_case, membership_repo, *_ = _build(
        [OrgRole.SUPERADMIN, OrgRole.ADMIN], superadmin_count=2
    )

    await _execute(use_case, [OrgRole.ADMIN], superuser=True)

    membership_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_granting_superadmin_is_audited():
    use_case, _, _, audit_log_repo = _build(
        [OrgRole.ADMIN], actor_roles=[OrgRole.SUPERADMIN, OrgRole.ADMIN]
    )

    await _execute(use_case, [OrgRole.SUPERADMIN, OrgRole.ADMIN])

    assert audit_log_repo.log.call_args.args[0].action == SUPERADMIN_ROLE_GRANTED


@pytest.mark.asyncio
async def test_changes_without_superadmin_are_not_audited():
    use_case, _, _, audit_log_repo = _build(
        [OrgRole.MEMBER], actor_roles=[OrgRole.SUPERADMIN, OrgRole.ADMIN]
    )

    await _execute(use_case, [OrgRole.MEMBER, OrgRole.CONTENT_MANAGER])

    audit_log_repo.log.assert_not_called()
