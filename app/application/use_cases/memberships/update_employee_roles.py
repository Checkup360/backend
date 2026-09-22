import uuid

from app.domain.entities import Employee
from app.domain.exceptions import (
    InsufficientRolePermissionError,
    MembershipNotFoundError,
    NotOrganizationAdminError,
    OrganizationNotFoundError,
    SuperadminDirectRemovalForbiddenError,
)
from app.domain.repositories import (
    MembershipRepository,
    OrganizationRepository,
    RefreshTokenRepository,
)
from app.domain.value_objects import OrgRole


class UpdateEmployeeRolesUseCase:
    def __init__(
        self,
        membership_repo: MembershipRepository,
        org_repo: OrganizationRepository,
        refresh_token_repo: RefreshTokenRepository,
    ):
        self.membership_repo = membership_repo
        self.org_repo = org_repo
        self.refresh_token_repo = refresh_token_repo

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

        target_roles = target_membership.roles
        is_target_superadmin = OrgRole.SUPERADMIN in target_roles
        is_target_admin = OrgRole.ADMIN in target_roles or is_target_superadmin

        if not actor_is_superuser:
            actor_membership = await self.membership_repo.get_by_user_and_org(
                actor_user_id, organization_id
            )
            if not actor_membership:
                raise NotOrganizationAdminError()

            actor_roles = actor_membership.roles
            is_actor_superadmin = OrgRole.SUPERADMIN in actor_roles
            is_actor_admin = OrgRole.ADMIN in actor_roles or is_actor_superadmin

            if not is_actor_admin:
                raise NotOrganizationAdminError()

            if not is_actor_superadmin:
                # Regular admin cannot modify an admin or superadmin
                if is_target_admin or is_target_superadmin:
                    raise InsufficientRolePermissionError(
                        "Regular admin cannot modify roles of an admin or superadmin"
                    )
                # Regular admin cannot grant admin or superadmin
                if OrgRole.ADMIN in new_roles or OrgRole.SUPERADMIN in new_roles:
                    raise InsufficientRolePermissionError(
                        "Regular admin cannot grant admin or superadmin roles"
                    )
            else:
                # Actor is superadmin: cannot remove superadmin directly (requires quorum)
                if is_target_superadmin and OrgRole.SUPERADMIN not in new_roles:
                    raise SuperadminDirectRemovalForbiddenError(
                        "Removing a superadmin requires quorum voting"
                    )

        # Immediate session revocation if losing member role or all roles
        losing_member_role = (
            OrgRole.MEMBER in target_roles and OrgRole.MEMBER not in new_roles
        )
        losing_all_roles = len(new_roles) == 0

        if losing_member_role or losing_all_roles:
            await self.refresh_token_repo.revoke_all_for_user(target_user_id)

        target_membership.roles = new_roles
        await self.membership_repo.save(target_membership)
        employee = await self.membership_repo.get_employee(
            target_user_id, organization_id
        )
        if not employee:
            raise MembershipNotFoundError()
        return employee
