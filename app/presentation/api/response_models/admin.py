import uuid
from datetime import datetime

from pydantic import BaseModel


class CreateInviteResponse(BaseModel):
    token: str
    invite_url: str


class DeleteInvitesResponse(BaseModel):
    deleted_count: int


class SysadminInviteResponse(BaseModel):
    id: uuid.UUID
    token: str
    email: str | None
    max_uses: int
    uses: int
    expires_at: datetime
    invite_url: str
