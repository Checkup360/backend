import datetime
import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
    BackgroundTasks,
)
from pydantic import BaseModel

from app.auth.authorization import require_superuser
from app.dependencies import get_invite_service, get_email_service
from app.domain.services.invite import InviteService, build_invite_url
from app.domain.services.email_service import EmailService
from app.persistence.models import User

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateSysadminInviteRequest(BaseModel):
    email: str | None = None
    expires_in_hours: int = 24


class CreateInviteResponse(BaseModel):
    token: str
    invite_url: str


class DeleteInvitesRequest(BaseModel):
    ids: list[uuid.UUID]


class DeleteInvitesResponse(BaseModel):
    deleted_count: int


@router.post("/invites", response_model=CreateInviteResponse)
async def create_sysadmin_invite(
    request: CreateSysadminInviteRequest,
    background_tasks: BackgroundTasks,
    service: InviteService = Depends(get_invite_service),
    email_service: EmailService = Depends(get_email_service),
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

    invite_url = build_invite_url(invite.token)

    if request.email:
        background_tasks.add_task(
            email_service.send_invite_email,
            to_email=request.email,
            invite_url=invite_url,
            is_sysadmin=True,
            role="sysadmin",
        )

    return CreateInviteResponse(
        token=invite.token,
        invite_url=invite_url,
    )


class SysadminInviteResponse(BaseModel):
    id: uuid.UUID
    token: str
    email: str | None
    max_uses: int
    uses: int
    expires_at: datetime.datetime
    invite_url: str


@router.get("/invites", response_model=list[SysadminInviteResponse])
async def list_sysadmin_invites(
    response: Response,
    status: str | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    service: InviteService = Depends(get_invite_service),
    current_user: User = Depends(require_superuser),
):
    """
    Lista las invitaciones de sysadmin creadas en la plataforma.
    """
    from sqlalchemy import func, select
    from app.persistence.models.invite import InviteToken as InviteTokenORM
    from datetime import timezone

    query = select(InviteTokenORM).where(InviteTokenORM.is_sysadmin.is_(True))

    if status is not None:
        status_val = status.lower()
        now = datetime.now(timezone.utc)
        if status_val == "used":
            query = query.where(InviteTokenORM.uses >= InviteTokenORM.max_uses)
        elif status_val == "expired":
            query = query.where(
                InviteTokenORM.uses < InviteTokenORM.max_uses,
                InviteTokenORM.expires_at <= now,
            )
        elif status_val == "active":
            query = query.where(
                InviteTokenORM.uses < InviteTokenORM.max_uses,
                InviteTokenORM.expires_at > now,
            )

    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    total = await service.invite_repo.db.scalar(count_query)
    query = query.order_by(InviteTokenORM.created_at.desc())
    response.headers["X-Total-Count"] = str(total or 0)
    response.headers["X-Page-Size"] = str(page_size)
    if page is not None:
        response.headers["X-Page"] = str(page)
        query = query.offset((page - 1) * page_size).limit(page_size)
    else:
        response.headers["X-Page"] = "1"
    result = await service.invite_repo.db.scalars(query)
    orms = result.all()

    return [
        SysadminInviteResponse(
            id=orm.id,
            token=orm.token,
            email=orm.email,
            max_uses=orm.max_uses,
            uses=orm.uses,
            expires_at=orm.expires_at,
            invite_url=build_invite_url(orm.token),
        )
        for orm in orms
    ]


@router.delete("/invites", response_model=DeleteInvitesResponse)
async def delete_sysadmin_invites(
    request: DeleteInvitesRequest,
    service: InviteService = Depends(get_invite_service),
    current_user: User = Depends(require_superuser),
):
    if not request.ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invite_ids_required",
        )

    from sqlalchemy import delete
    from app.persistence.models.invite import InviteToken as InviteTokenORM

    result = await service.invite_repo.db.execute(
        delete(InviteTokenORM).where(
            InviteTokenORM.id.in_(request.ids),
            InviteTokenORM.is_sysadmin.is_(True),
        )
    )
    await service.invite_repo.db.commit()
    return DeleteInvitesResponse(deleted_count=result.rowcount or 0)
