from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.authorization import require_superuser
from app.dependencies import get_invite_service
from app.domain.services.invite import InviteService, build_invite_url
from app.persistence.models import User

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
    service: InviteService = Depends(get_invite_service),
    current_user: User = Depends(require_superuser),
):
    """
    Crea una invitación para un nuevo sysadmin.
    Si se proporciona un email, el token solo es válido para ese email.
    El token expira en `expires_in_hours` horas.
    """
    invite = await service.create_invite(
        email=request.email,
        max_uses=1,
        expires_in_hours=request.expires_in_hours,
        organization_id=None,
        role=None,
        is_sysadmin=True,
    )

    return CreateInviteResponse(
        token=invite.token,
        invite_url=build_invite_url(invite.token),
    )
