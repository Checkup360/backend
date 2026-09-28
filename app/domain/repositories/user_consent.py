from abc import ABC, abstractmethod
from datetime import datetime
import uuid

from app.domain.entities.user_consent import ConsentType, UserConsent


class UserConsentRepository(ABC):
    """Domain repository interface for user consents."""

    @abstractmethod
    async def get_by_id(self, consent_id: uuid.UUID) -> UserConsent | None:
        pass

    @abstractmethod
    async def get_active_consent(
        self,
        user_id: uuid.UUID,
        consent_type: ConsentType,
        form_type: str | None = None,
    ) -> UserConsent | None:
        """Returns the current active (non-revoked) consent for the given user, type, and form_type."""
        pass

    @abstractmethod
    async def list_by_user_id(self, user_id: uuid.UUID) -> list[UserConsent]:
        """Lists all consent records (both active and revoked) for the given user."""
        pass

    @abstractmethod
    async def save(self, consent: UserConsent) -> UserConsent:
        pass

    @abstractmethod
    async def revoke(
        self, consent_id: uuid.UUID, revoked_at: datetime
    ) -> UserConsent | None:
        pass
