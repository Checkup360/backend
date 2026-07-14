from pydantic import BaseModel, EmailStr


class InvitePasswordRegisterBody(BaseModel):
    email: EmailStr
    password: str


class RedeemInviteBody(BaseModel):
    email: str | None = None
    password: str | None = None
