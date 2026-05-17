import uuid
from datetime import datetime

from pydantic import BaseModel

from app.domain.entities.org_role import OrgRole


class Membership(BaseModel):
    user_id: uuid.UUID
    organization_id: uuid.UUID
    role: OrgRole
    created_at: datetime | None = None
