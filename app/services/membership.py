import uuid
from typing import Optional

from fastapi import Depends

from app.models import Membership
from app.models.membership import OrgRole
from app.repositories.membership import MembershipRepository, get_membership_repository
from app.repositories.organization import (
    OrganizationRepository,
    get_organization_repository,
)


class MembershipService:
    def __init__(
        self,
        membership_repo: MembershipRepository,
        org_repo: OrganizationRepository,
    ):
        self.membership_repo = membership_repo
        self.org_repo = org_repo

    async def get_admin_membership(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Optional[Membership]:
        """
        Returns the membership if the user is an admin of the specified organization.
        """
        organization = await self.org_repo.get(organization_id)
        if not organization:
            return None

        membership = await self.membership_repo.get_by_user_and_org(
            user_id, organization_id
        )
        if not membership or membership.role != OrgRole.ADMIN:
            return None

        return membership

    async def is_admin_of_any(self, user_id: uuid.UUID) -> bool:
        return await self.membership_repo.is_admin_of_any(user_id)


async def get_membership_service(
    membership_repo: MembershipRepository = Depends(get_membership_repository),
    org_repo: OrganizationRepository = Depends(get_organization_repository),
) -> MembershipService:
    return MembershipService(membership_repo, org_repo)
