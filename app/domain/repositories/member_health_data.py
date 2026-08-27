import uuid
from typing import Protocol

from app.domain.entities.member_health_data import MemberHealthData


class MemberHealthDataRepository(Protocol):
    async def get_by_user(self, user_id: uuid.UUID) -> MemberHealthData | None:
        """Fetch member health data by user ID."""
        ...

    async def save(self, health_data: MemberHealthData) -> None:
        """Create or update member health data."""
        ...
