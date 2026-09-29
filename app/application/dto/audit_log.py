from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import uuid


@dataclass
class AuditLogEntryDTO:
    id: uuid.UUID
    user_id: uuid.UUID | None
    organization_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    details: dict[str, Any]
    created_at: datetime
    user_email: str | None = None
    user_name: str | None = None


@dataclass
class AuditLogListDTO:
    items: list[AuditLogEntryDTO]
    total: int
    page: int
    page_size: int
    has_next: bool


@dataclass
class OrganizationComplianceSummaryDTO:
    total_audit_events: int
    consent_accepted_count: int
    consent_revoked_count: int
    data_exported_count: int
    audited_members_count: int
    actions_breakdown: dict[str, int] = field(default_factory=dict)
