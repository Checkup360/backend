from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
import uuid

from app.application.dto.consent import UserConsentDTO


@dataclass
class MemberDataExportDTO:
    user_id: uuid.UUID
    email: str
    first_name: str | None
    last_name: str | None
    phone_number: str | None
    date_of_birth: date | str | None
    avatar_url: str | None
    organization_id: uuid.UUID | None
    organization_name: str | None
    roles: list[str]
    consents: list[UserConsentDTO]
    health_data: dict[str, Any] | None
    assessment_submissions: list[dict[str, Any]]
    risk_scores: list[dict[str, Any]]
    exported_at: datetime
    compliance_notice: str = (
        "Exported in compliance with Argentine Law 25.326 (Habeas Data / Right of Access) "
        "and international medical data protection standards."
    )
