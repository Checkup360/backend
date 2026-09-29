from datetime import date, datetime
from typing import Any
from pydantic import BaseModel, ConfigDict


class ExportedProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    date_of_birth: date | str | None = None
    avatar_url: str | None = None
    organization: str | None = None
    roles: list[str] = []


class ExportedConsentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str
    version: str | None = None
    accepted_at: datetime
    revoked_at: datetime | None = None
    status: str


class ExportedSubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    form_type: str
    form_name: str
    form_version: str
    status: str
    submitted_at: datetime | str | None = None
    answers: dict[str, Any] = {}


class ExportedEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    indicator: str
    risk_level: str | None = None
    evaluated_at: datetime | str | None = None


class MemberDataExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    profile: ExportedProfileResponse
    consents: list[ExportedConsentResponse] = []
    health_measurements: dict[str, Any] = {}
    assessment_history: list[ExportedSubmissionResponse] = []
    health_evaluations: list[ExportedEvaluationResponse] = []
    exported_at: datetime
    compliance_notice: str
