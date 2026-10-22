import uuid
from dataclasses import dataclass
from datetime import datetime

from app.domain.entities.department import Department
from app.domain.value_objects import OrgRole


@dataclass(frozen=True)
class EmployeeSummary:
    """Row of the employee directory an organization admin browses."""

    user_id: uuid.UUID
    email: str
    roles: list[OrgRole]
    status: str | None
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    department: Department | None = None
    last_assessment: datetime | None = None
    overall_health_index: float | None = None
