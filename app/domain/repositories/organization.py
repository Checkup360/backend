import uuid
from typing import Protocol

from app.domain.entities import Organization


class OrganizationRepository(Protocol):
    async def get(self, id: uuid.UUID) -> Organization | None: ...

    async def get_by_slug(self, slug: str) -> Organization | None: ...

    async def create(self, **values) -> Organization: ...

    async def search(
        self,
        status: str | None = None,
        search: str | None = None,
        page: int | None = None,
        page_size: int = 10,
    ) -> tuple[list[Organization], int]: ...

    async def list(self) -> list[Organization]: ...

    async def delete(self, id: uuid.UUID) -> bool: ...

    async def update(self, id: uuid.UUID, **kwargs) -> Organization | None: ...

    async def update_score_weights(
        self,
        id: uuid.UUID,
        score_weights: dict[str, float],
        risk_thresholds: dict[str, float] | None = None,
    ) -> Organization | None: ...
