from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict


class UserConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    consent_type: str
    form_type: str | None = None
    document_version: str
    document_hash: str | None = None
    accepted_at: datetime
    revoked_at: datetime | None = None


class ActiveConsentsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    terms_and_conditions: UserConsentResponse | None = None
    privacy_policy: UserConsentResponse | None = None
    health_data_processing: UserConsentResponse | None = None
    form_consents: dict[str, UserConsentResponse] = {}
