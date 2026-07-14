import uuid
from typing import Protocol

from app.domain.entities import User


class UserRepository(Protocol):
    async def get(self, id: uuid.UUID) -> User | None: ...

    async def update(self, id: uuid.UUID, **values) -> User | None: ...
