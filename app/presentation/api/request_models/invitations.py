import uuid

from pydantic import BaseModel

from app.domain.value_objects import OrgRole


class CreateOrganizationInviteRequest(BaseModel):
    email: str | None = None
    expires_in_hours: int = 24
    max_uses: int = 1
    organization_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    role: OrgRole
    is_superadmin: bool = False


class DeleteInvitesRequest(BaseModel):
    ids: list[uuid.UUID]
