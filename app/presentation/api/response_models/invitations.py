import uuid
from datetime import datetime

from pydantic import BaseModel


class OrganizationInviteResponse(BaseModel):
    id: uuid.UUID
    token: str
    email: str | None = None
    role: str | None = None
    is_superadmin: bool = False
    organization_id: uuid.UUID | None = None
    organization_name: str | None = None
    department_id: uuid.UUID | None = None
    department_name: str | None = None
    max_uses: int
    uses: int
    expires_at: datetime
    invite_url: str


class CreateInviteResponse(BaseModel):
    token: str
    invite_url: str


class DeleteInvitesResponse(BaseModel):
    deleted_count: int


class InviteMetadataResponse(BaseModel):
    organization_id: uuid.UUID | None = None
    organization_name: str | None = None
    role: str | None = None
    is_sysadmin: bool = False
    is_superadmin: bool = False


class RedeemResponse(BaseModel):
    ok: bool = True
