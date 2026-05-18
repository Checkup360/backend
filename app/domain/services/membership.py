import uuid

from app.domain.entities import Membership
from app.domain.entities.org_role import OrgRole
from app.domain.exceptions import (
    NotOrganizationAdminError,
    OrganizationNotFoundError,
)
from app.persistence.repositories.membership import MembershipRepository
from app.persistence.repositories.organization import OrganizationRepository


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
    ) -> Membership:
        organization = await self.org_repo.get(organization_id)
        if not organization:
            raise OrganizationNotFoundError()

        membership = await self.membership_repo.get_by_user_and_org(
            user_id, organization_id
        )
        if not membership or membership.role != OrgRole.ADMIN:
            raise NotOrganizationAdminError()

        return membership

    async def is_admin_of_any(self, user_id: uuid.UUID) -> bool:
        return await self.membership_repo.is_admin_of_any(user_id)
