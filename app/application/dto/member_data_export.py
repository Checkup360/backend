from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class ExportedProfileDTO:
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    date_of_birth: date | str | None = None
    avatar_url: str | None = None
    organization: str | None = None
    roles: list[str] = field(default_factory=list)


@dataclass
class ExportedConsentDTO:
    type: str
    version: str | None
    accepted_at: datetime
    revoked_at: datetime | None
    status: str  # "Active" or "Revoked"


@dataclass
class ExportedSubmissionDTO:
    form_type: str
    form_name: str
    form_version: str
    status: str
    submitted_at: datetime | str | None
    answers: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExportedEvaluationDTO:
    indicator: str
    risk_level: str | None
    evaluated_at: datetime | str | None


@dataclass
class MemberDataExportDTO:
    profile: ExportedProfileDTO
    consents: list[ExportedConsentDTO]
    health_measurements: dict[str, Any]
    assessment_history: list[ExportedSubmissionDTO]
    health_evaluations: list[ExportedEvaluationDTO]
    exported_at: datetime
    compliance_notice: str = (
        "Exported in compliance with Argentine Law 25.326 (Habeas Data / Right of Access) "
        "and international health data protection standards."
    )
