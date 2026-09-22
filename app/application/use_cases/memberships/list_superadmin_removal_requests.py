import uuid

from app.domain.entities.superadmin_removal import (
    RemovalRequestStatus,
    SuperadminRemovalRequest,
)
from app.domain.exceptions import (
    InsufficientRolePermissionError,
    NotOrganizationAdminError,
    OrganizationNotFoundError,
)
from app.domain.repositories import (
    MembershipRepository,
    OrganizationRepository,
)
from app.domain.repositories.superadmin_removal import (
    SuperadminRemovalRepository,
)
from app.domain.value_objects import OrgRole


class ListSuperadminRemovalRequestsUseCase:
    def __init__(
        self,
        membership_repo: MembershipRepository,
        org_repo: OrganizationRepository,
        removal_repo: SuperadminRemovalRepository,
    ):
        self.membership_repo = membership_repo
        self.org_repo = org_repo
        self.removal_repo = removal_repo

    async def execute(
        self,
        actor_user_id: uuid.UUID,
        actor_is_superuser: bool,
        organization_id: uuid.UUID,
        status: RemovalRequestStatus | None = None,
    ) -> list[SuperadminRemovalRequest]:
        organization = await self.org_repo.get(organization_id)
        if not organization:
            raise OrganizationNotFoundError()

        if not actor_is_superuser:
            actor_membership = await self.membership_repo.get_by_user_and_org(
                actor_user_id, organization_id
            )
            if not actor_membership:
                raise NotOrganizationAdminError()

            if OrgRole.SUPERADMIN not in actor_membership.roles:
                raise InsufficientRolePermissionError(
                    "Only superadmins can view removal requests"
                )

        return await self.removal_repo.list_requests_for_organization(
            organization_id, status=status
        )
