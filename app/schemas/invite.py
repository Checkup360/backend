from pydantic import BaseModel, EmailStr, Field


class PrepareGoogleSessionResponse(BaseModel):
    ok: bool


class InviteRejected(BaseModel):
    """Invite inválido, expirado, ya usado o email distinto al de la invitación."""

    code: str = Field(
        ...,
        description="no_invite | invalid_invite | invite_used | invite_expired | email_mismatch",
    )


class InvitePasswordRegisterBody(BaseModel):
    email: EmailStr
    password: str
