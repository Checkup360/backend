import uuid
from typing import Protocol

from app.domain.entities import InviteToken
from app.domain.value_objects import OrgRole


class InviteRepository(Protocol):
    async def get(self, id: uuid.UUID) -> InviteToken | None: ...

    async def get_by_token(self, token: str) -> InviteToken | None: ...

    async def save(self, entity: InviteToken) -> InviteToken: ...

    async def update(self, id: uuid.UUID, **values) -> InviteToken | None: ...

    async def list_filtered(
        self,
        *,
        organization_id: uuid.UUID | None,
        is_sysadmin: bool,
        role: OrgRole | None,
        status: str | None,
        page: int | None,
        page_size: int,
    ) -> tuple[list[InviteToken], int]: ...

    async def delete_filtered(
        self,
        *,
        ids: list[uuid.UUID],
        is_sysadmin: bool,
        organization_id: uuid.UUID | None,
    ) -> int: ...
