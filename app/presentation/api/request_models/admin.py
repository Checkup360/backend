import uuid

from pydantic import BaseModel


class CreateSysadminInviteRequest(BaseModel):
    email: str | None = None
    expires_in_hours: int = 24


class DeleteInvitesRequest(BaseModel):
    ids: list[uuid.UUID]
