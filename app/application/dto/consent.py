from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass
class UserConsentDTO:
    id: uuid.UUID
    user_id: uuid.UUID
    consent_type: str
    document_version: str
    accepted_at: datetime
    form_type: str | None = None
    document_id: uuid.UUID | None = None
    document_hash: str | None = None
    revoked_at: datetime | None = None
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass
class ActiveConsentsDTO:
    terms_and_conditions: UserConsentDTO | None
    privacy_policy: UserConsentDTO | None
    health_data_processing: UserConsentDTO | None
    form_consents: dict[str, UserConsentDTO]
