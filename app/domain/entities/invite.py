import uuid
from datetime import datetime

from pydantic import BaseModel

from app.domain.entities.org_role import OrgRole
from app.domain.entities.organization import Organization


class InviteToken(BaseModel):
    id: uuid.UUID
    token: str
    email: str | None = None
    max_uses: int = 1
    uses: int = 0
    expires_at: datetime
    organization_id: uuid.UUID | None = None
    organization: Organization | None = None
    role: OrgRole | None = None
    is_sysadmin: bool = False

    @property
    def is_exhausted(self) -> bool:
        return self.uses >= self.max_uses
