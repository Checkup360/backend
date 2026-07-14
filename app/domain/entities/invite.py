import uuid
from dataclasses import dataclass
from datetime import datetime

from app.domain.value_objects import OrgRole
from app.domain.entities.department import Department
from app.domain.entities.organization import Organization


@dataclass
class InviteToken:
    id: uuid.UUID
    token: str
    expires_at: datetime
    email: str | None = None
    max_uses: int = 1
    uses: int = 0
    organization_id: uuid.UUID | None = None
    organization: Organization | None = None
    department_id: uuid.UUID | None = None
    department: Department | None = None
    role: OrgRole | None = None
    is_sysadmin: bool = False

    @property
    def is_exhausted(self) -> bool:
        return self.uses >= self.max_uses
