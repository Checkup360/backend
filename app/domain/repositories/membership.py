import uuid
from typing import Protocol

from app.domain.entities import Employee, Membership
from app.domain.value_objects import MembershipState, OrgRole


class MembershipRepository(Protocol):
    async def get_by_user(self, user_id: uuid.UUID) -> Membership | None: ...

    async def get_by_user_and_org(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Membership | None: ...

    async def is_admin_of_any(self, user_id: uuid.UUID) -> bool: ...

    async def list_members_for_organization(
        self,
        organization_id: uuid.UUID,
        roles: list[OrgRole] | None = None,
        state: MembershipState = MembershipState.ALL,
    ) -> list[Employee]: ...

    async def get_employee(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Employee | None: ...

    async def count_members_for_organization(
        self, organization_id: uuid.UUID, roles: list[OrgRole] | None = None
    ) -> int: ...

    async def count_superadmins(self, organization_id: uuid.UUID) -> int: ...

    async def save(self, entity: Membership) -> Membership: ...
