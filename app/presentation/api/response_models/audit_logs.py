from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field


class AuditLogItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None = None
    user_email: str | None = None
    user_name: str | None = None
    organization_id: uuid.UUID | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AuditLogListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[AuditLogItemResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class ConsentComplianceSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_audit_events: int
    consent_accepted_count: int
    consent_revoked_count: int
    data_exported_count: int
    audited_members_count: int
    actions_breakdown: dict[str, int] = Field(default_factory=dict)
