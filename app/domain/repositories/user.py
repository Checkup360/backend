import uuid
from typing import Protocol

from app.domain.entities import MemberDetails, User


class UserRepository(Protocol):
    async def get(self, id: uuid.UUID) -> User | None: ...

    async def update(self, id: uuid.UUID, **values) -> User | None: ...

    async def list_sysadmins(
        self,
        search: str | None = None,
        is_active: bool | None = None,
        page: int | None = None,
        page_size: int = 10,
    ) -> tuple[list[tuple[User, MemberDetails | None]], int]: ...

    async def count_sysadmins(self, is_active: bool | None = None) -> int: ...
