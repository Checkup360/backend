from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import uuid


class ConsentType(str, Enum):
    TERMS_AND_CONDITIONS = "TERMS_AND_CONDITIONS"
    PRIVACY_POLICY = "PRIVACY_POLICY"
    HEALTH_DATA_PROCESSING_CONSENT = "HEALTH_DATA_PROCESSING_CONSENT"
    FORM_CONSENT = "FORM_CONSENT"


@dataclass
class UserConsent:
    id: uuid.UUID
    user_id: uuid.UUID
    consent_type: ConsentType
    document_version: str
    accepted_at: datetime
    form_type: str | None = None
    document_id: uuid.UUID | None = None
    document_hash: str | None = None
    revoked_at: datetime | None = None
    ip_address: str | None = None
    user_agent: str | None = None

    @property
    def is_active(self) -> bool:
        """Returns True if the consent has not been revoked."""
        return self.revoked_at is None
