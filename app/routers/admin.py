import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.authorization import require_superuser
from app.database import get_db
from app.invites.service import build_invite_token, build_invite_url
from app.models import Organization, User
from app.models.membership import OrgRole

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateInviteRequest(BaseModel):
    email: str | None = None
    expires_in_hours: int = 24
    max_uses: int = 1
    organization_id: uuid.UUID | None = None
    role: OrgRole | None = None
    is_sysadmin: bool = False


class CreateInviteResponse(BaseModel):
    token: str
    invite_url: str


@router.post("/invites", response_model=CreateInviteResponse)
async def create_invite(
    request: CreateInviteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_superuser),
):
    """
    Genera un nuevo invite token.
    Si se proporciona un email, el token solo es válido para ese email.
    El token expira en `expires_in_hours` horas.
    """
    if request.role and not request.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="role_requires_organization",
        )

    if request.organization_id:
        organization = await db.get(Organization, request.organization_id)
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="organization_not_found",
            )

    invite = build_invite_token(
        email=request.email,
        max_uses=request.max_uses,
        expires_in_hours=request.expires_in_hours,
        organization_id=request.organization_id,
        role=request.role,
        is_sysadmin=request.is_sysadmin,
    )

    db.add(invite)
    await db.commit()

    return CreateInviteResponse(
        token=invite.token,
        invite_url=build_invite_url(invite.token),
    )
