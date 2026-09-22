import uuid

from app.domain.entities import Employee, Membership
from app.domain.value_objects import OrgRole
from app.domain.exceptions import (
    NotOrganizationAdminError,
    OrganizationNotFoundError,
)
from app.domain.repositories import MembershipRepository, OrganizationRepository


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
        is_admin = bool(
            membership
            and (
                OrgRole.ADMIN in membership.roles
                or OrgRole.SUPERADMIN in membership.roles
            )
        )
        if not is_admin:
            raise NotOrganizationAdminError()

        return membership

    async def is_admin_of_any(self, user_id: uuid.UUID) -> bool:
        return await self.membership_repo.is_admin_of_any(user_id)

    async def list_employees_for_organization_admin(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        roles: list[OrgRole] | None = None,
    ) -> list[Employee]:
        await self.get_admin_membership(user_id, organization_id)
        return await self.membership_repo.list_members_for_organization(
            organization_id, roles=roles
        )

    async def count_employees_for_organization_admin(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
        roles: list[OrgRole] | None = None,
    ) -> int:
        await self.get_admin_membership(user_id, organization_id)
        return await self.membership_repo.count_members_for_organization(
            organization_id, roles=roles
        )

    async def count_members_for_organization(
        self,
        organization_id: uuid.UUID,
        roles: list[OrgRole] | None = None,
    ) -> int:
        return await self.membership_repo.count_members_for_organization(
            organization_id, roles=roles
        )
