from datetime import date, datetime
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict

from app.presentation.api.response_models.consents import UserConsentResponse


class MemberDataExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    date_of_birth: date | str | None = None
    avatar_url: str | None = None
    organization_id: uuid.UUID | None = None
    organization_name: str | None = None
    roles: list[str] = []
    consents: list[UserConsentResponse] = []
    health_data: dict[str, Any] | None = None
    assessment_submissions: list[dict[str, Any]] = []
    risk_scores: list[dict[str, Any]] = []
    exported_at: datetime
    compliance_notice: str
