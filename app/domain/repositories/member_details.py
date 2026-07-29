import uuid
from typing import Protocol

from app.domain.entities import MemberDetails


class MemberDetailsRepository(Protocol):
    async def exists_for_user(self, user_id: uuid.UUID) -> bool: ...

    async def get_by_user(self, user_id: uuid.UUID) -> MemberDetails | None: ...

    async def save(self, entity: MemberDetails) -> MemberDetails: ...
