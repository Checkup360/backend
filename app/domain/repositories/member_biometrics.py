import uuid
from typing import Protocol

from app.domain.entities.member_biometrics import MemberBiometrics


class MemberBiometricsRepository(Protocol):
    async def get_by_user(self, user_id: uuid.UUID) -> MemberBiometrics | None:
        """Fetch member biometrics by user ID."""
        ...

    async def save(self, biometrics: MemberBiometrics) -> None:
        """Create or update member biometrics."""
        ...
