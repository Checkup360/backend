import uuid

from app.domain.entities import Employee
from app.domain.entities.audit_log import AuditLog
from app.domain.entities.membership import Membership
from app.domain.exceptions import (
    InsufficientRolePermissionError,
    MembershipNotFoundError,
    NotOrganizationAdminError,
    OrganizationNotFoundError,
)
from app.domain.repositories import (
    MembershipRepository,
    OrganizationRepository,
    RefreshTokenRepository,
)
from app.domain.repositories.audit_log import AuditLogRepository
from app.domain.services.superadmin_policy import (
    ensure_not_self_removal,
    ensure_superadmin_remains,
)
from app.domain.value_objects import OrgRole

SUPERADMIN_ROLE_GRANTED = "SUPERADMIN_ROLE_GRANTED"
SUPERADMIN_ROLE_REMOVED = "SUPERADMIN_ROLE_REMOVED"
MEMBERSHIP_RESOURCE = "MEMBERSHIP"


class UpdateEmployeeRolesUseCase:
    def __init__(
        self,
        membership_repo: MembershipRepository,
        org_repo: OrganizationRepository,
        refresh_token_repo: RefreshTokenRepository,
        audit_log_repo: AuditLogRepository,
    ):
        self.membership_repo = membership_repo
        self.org_repo = org_repo
        self.refresh_token_repo = refresh_token_repo
        self.audit_log_repo = audit_log_repo

    async def execute(
        self,
        actor_user_id: uuid.UUID,
        actor_is_superuser: bool,
        organization_id: uuid.UUID,
        target_user_id: uuid.UUID,
        new_roles: list[OrgRole],
    ) -> Employee:
        organization = await self.org_repo.get(organization_id)
        if not organization:
            raise OrganizationNotFoundError()

        target_membership = await self.membership_repo.get_by_user_and_org(
            target_user_id, organization_id
        )
        if not target_membership:
            raise MembershipNotFoundError()

        previous_roles = list(target_membership.roles)
        if not actor_is_superuser:
            await self._ensure_actor_can_change_roles(
                actor_user_id, organization_id, previous_roles, new_roles
            )
        if _loses_role(OrgRole.SUPERADMIN, previous_roles, new_roles):
            await self._ensure_superadmin_removal_allowed(
                actor_user_id, actor_is_superuser, target_membership
            )

        await self._revoke_sessions_if_access_is_lost(
            target_user_id, previous_roles, new_roles
        )
        target_membership.roles = new_roles
        await self.membership_repo.save(target_membership)
        await self._record_superadmin_change(
            actor_user_id, target_membership, previous_roles, new_roles
        )

        employee = await self.membership_repo.get_employee(
            target_user_id, organization_id
        )
        if not employee:
            raise MembershipNotFoundError()
        return employee

    async def _ensure_actor_can_change_roles(
        self,
        actor_user_id: uuid.UUID,
        organization_id: uuid.UUID,
        target_roles: list[OrgRole],
        new_roles: list[OrgRole],
    ) -> None:
        actor_membership = await self.membership_repo.get_by_user_and_org(
            actor_user_id, organization_id
        )
        if not actor_membership:
            raise NotOrganizationAdminError()

        actor_roles = actor_membership.roles
        if OrgRole.SUPERADMIN in actor_roles:
            return
        if OrgRole.ADMIN not in actor_roles:
            raise NotOrganizationAdminError()
        if _is_admin(target_roles):
            raise InsufficientRolePermissionError(
                "Regular admin cannot modify roles of an admin or superadmin"
            )
        if _is_admin(new_roles):
            raise InsufficientRolePermissionError(
                "Regular admin cannot grant admin or superadmin roles"
            )

    async def _ensure_superadmin_removal_allowed(
        self,
        actor_user_id: uuid.UUID,
        actor_is_superuser: bool,
        target_membership: Membership,
    ) -> None:
        # Platform sysadmins may intervene on any superadmin, but an
        # organization is never left without one.
        if not actor_is_superuser:
            ensure_not_self_removal(actor_user_id, target_membership.user_id)
        current_count = await self.membership_repo.count_superadmins(
            target_membership.organization_id
        )
        ensure_superadmin_remains(current_count)

    async def _revoke_sessions_if_access_is_lost(
        self,
        target_user_id: uuid.UUID,
        previous_roles: list[OrgRole],
        new_roles: list[OrgRole],
    ) -> None:
        losing_member_role = _loses_role(OrgRole.MEMBER, previous_roles, new_roles)
        if losing_member_role or len(new_roles) == 0:
            await self.refresh_token_repo.revoke_all_for_user(target_user_id)

    async def _record_superadmin_change(
        self,
        actor_user_id: uuid.UUID,
        target_membership: Membership,
        previous_roles: list[OrgRole],
        new_roles: list[OrgRole],
    ) -> None:
        if _loses_role(OrgRole.SUPERADMIN, previous_roles, new_roles):
            action = SUPERADMIN_ROLE_REMOVED
        elif _loses_role(OrgRole.SUPERADMIN, new_roles, previous_roles):
            action = SUPERADMIN_ROLE_GRANTED
        else:
            return

        await self.audit_log_repo.log(
            AuditLog.create(
                action=action,
                resource_type=MEMBERSHIP_RESOURCE,
                user_id=actor_user_id,
                organization_id=target_membership.organization_id,
                resource_id=str(target_membership.user_id),
            )
        )


def _loses_role(
    role: OrgRole, previous_roles: list[OrgRole], new_roles: list[OrgRole]
) -> bool:
    return role in previous_roles and role not in new_roles


def _is_admin(roles: list[OrgRole]) -> bool:
    return OrgRole.ADMIN in roles or OrgRole.SUPERADMIN in roles
