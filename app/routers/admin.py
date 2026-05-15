from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.authorization import require_superuser
from app.invites.service import build_invite_token, build_invite_url
from app.models import User
from app.repositories.invite import InviteRepository, get_invite_repository

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateSysadminInviteRequest(BaseModel):
    email: str | None = None
    expires_in_hours: int = 24


class CreateInviteResponse(BaseModel):
    token: str
    invite_url: str


@router.post("/invites", response_model=CreateInviteResponse)
async def create_sysadmin_invite(
    request: CreateSysadminInviteRequest,
    repo: InviteRepository = Depends(get_invite_repository),
    current_user: User = Depends(require_superuser),
):
    """
    Crea una invitación para un nuevo sysadmin.
    Si se proporciona un email, el token solo es válido para ese email.
    El token expira en `expires_in_hours` horas.
    """
    invite = build_invite_token(
        email=request.email,
        max_uses=1,
        expires_in_hours=request.expires_in_hours,
        organization_id=None,
        role=None,
        is_sysadmin=True,
    )

    await repo.save(invite)

    return CreateInviteResponse(
        token=invite.token,
        invite_url=build_invite_url(invite.token),
    )
