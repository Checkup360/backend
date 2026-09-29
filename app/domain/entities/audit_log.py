from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass
class AuditLog:
    id: uuid.UUID
    user_id: uuid.UUID | None
    organization_id: uuid.UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    details: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        action: str,
        resource_type: str,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> "AuditLog":
        return cls(
            id=uuid.uuid4(),
            user_id=user_id,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            created_at=datetime.now(timezone.utc),
        )
