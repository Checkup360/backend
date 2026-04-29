import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import InviteToken

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateInviteRequest(BaseModel):
    email: str | None = None
    expires_in_hours: int = 24


class CreateInviteResponse(BaseModel):
    token: str
    invite_url: str


@router.post("/invites", response_model=CreateInviteResponse)
async def create_invite(
    request: CreateInviteRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Genera un nuevo invite token.
    Si se proporciona un email, el token solo es válido para ese email.
    El token expira en `expires_in_hours` horas.
    """
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=request.expires_in_hours)

    invite = InviteToken(
        token=token,
        email=request.email,
        expires_at=expires_at,
    )

    db.add(invite)
    await db.commit()

    # Magic link: /invite/[token] redirige a /auth/google/authorize?invite_token=xxx
    invite_url = f"http://localhost:5173/invite/{token}"

    return CreateInviteResponse(token=token, invite_url=invite_url)
