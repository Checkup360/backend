import uuid
from typing import Protocol

from app.domain.entities import MemberDetails


class MemberDetailsRepository(Protocol):
    async def exists_for_user(self, user_id: uuid.UUID) -> bool: ...

    async def save(self, entity: MemberDetails) -> MemberDetails: ...
