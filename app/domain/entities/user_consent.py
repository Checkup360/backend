from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import uuid


class ConsentType(str, Enum):
    TERMS_AND_CONDITIONS = "TERMS_AND_CONDITIONS"
    PRIVACY_POLICY = "PRIVACY_POLICY"
    HEALTH_DATA_PROCESSING_CONSENT = "HEALTH_DATA_PROCESSING_CONSENT"
    FORM_CONSENT = "FORM_CONSENT"


def normalize_version(version: str | None) -> str:
    """Normalizes a version string (e.g. '1.0' -> '1', '1.0.0' -> '1', '2.1.0' -> '2.1')."""
    if not version:
        return ""
    v = str(version).strip()
    parts = v.split(".")
    if all(p.isdigit() for p in parts):
        while len(parts) > 1 and parts[-1] == "0":
            parts.pop()
        return ".".join(parts)
    return v


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

    def matches_version(self, target_version: str | None) -> bool:
        """Returns True if the consent's document_version is compatible with target_version."""
        if not target_version:
            return False
        if self.document_version == target_version:
            return True
        return normalize_version(self.document_version) == normalize_version(
            target_version
        )
