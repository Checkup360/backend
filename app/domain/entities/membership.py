import uuid

from pydantic import BaseModel

from app.domain.entities.org_role import OrgRole


class Membership(BaseModel):
    user_id: uuid.UUID
    organization_id: uuid.UUID
    roles: list[OrgRole]
    department_id: uuid.UUID | None = None
