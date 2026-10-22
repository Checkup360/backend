import uuid
from typing import Protocol

from app.domain.entities import Department


class DepartmentRepository(Protocol):
    async def list_by_organization(
        self, organization_id: uuid.UUID
    ) -> list[Department]: ...

    async def search_by_organization(
        self,
        organization_id: uuid.UUID,
        search: str | None = None,
        page: int | None = None,
        page_size: int = 10,
    ) -> tuple[list[Department], int]: ...

    async def get_by_organization(
        self, organization_id: uuid.UUID, department_id: uuid.UUID
    ) -> Department | None: ...

    async def get_by_organization_and_slug(
        self, organization_id: uuid.UUID, slug: str
    ) -> Department | None: ...

    async def count_memberships(self, department_id: uuid.UUID) -> int: ...

    async def create(self, **values) -> Department: ...

    async def update(self, id: uuid.UUID, **values) -> Department | None: ...

    async def delete_by_organization(
        self, organization_id: uuid.UUID, department_id: uuid.UUID
    ) -> bool: ...
