from pydantic import BaseModel, Field


class PrepareGoogleSessionResponse(BaseModel):
    ok: bool


class InviteRejected(BaseModel):
    """An invitation rejected before it can be consumed."""

    code: str = Field(
        ...,
        description="no_invite | invalid_invite | invite_used | invite_expired | email_mismatch",
    )
