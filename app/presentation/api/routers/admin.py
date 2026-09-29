from datetime import datetime
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
from app.application.interfaces import EmailSender
from app.application.dto import AuthenticatedUser
from app.application.use_cases.invitations import (
    DeleteInvites,
    InviteUrlBuilder,
    ListInvites,
)
from app.application.use_cases.admin.list_sysadmins import ListSysadminsUseCase
from app.application.use_cases.audit import GetSystemAuditLogsUseCase
from app.presentation.api.authorization import require_superuser
from app.presentation.api.dependencies import (
    get_email_sender,
    get_delete_invites,
    get_invite_service,
    get_invite_url_builder,
    get_list_invites,
    get_list_sysadmins_use_case,
    get_get_system_audit_logs_use_case,
)
from app.domain.services.invite import InviteService
from app.presentation.api.request_models.admin import (
    CreateSysadminInviteRequest,
    DeleteInvitesRequest,
)
from app.presentation.api.response_models.admin import (
    CreateInviteResponse,
    DeleteInvitesResponse,
    SysadminInviteResponse,
    SysadminStatsResponse,
    SysadminUserResponse,
)
from app.presentation.api.response_models.audit_logs import (
    AuditLogItemResponse,
    AuditLogListResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/invites", response_model=CreateInviteResponse)
async def create_sysadmin_invite(
    request: CreateSysadminInviteRequest,
    background_tasks: BackgroundTasks,
    service: InviteService = Depends(get_invite_service),
    email_sender: EmailSender = Depends(get_email_sender),
    invite_url_builder: InviteUrlBuilder = Depends(get_invite_url_builder),
    current_user: AuthenticatedUser = Depends(require_superuser),
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

    invite_url = invite_url_builder.build(invite.token)

    if request.email:
        background_tasks.add_task(
            email_sender.send_invite_email,
            to_email=request.email,
            invite_url=invite_url,
            is_sysadmin=True,
            role="sysadmin",
        )

    return CreateInviteResponse(
        token=invite.token,
        invite_url=invite_url,
    )


@router.get("/invites", response_model=list[SysadminInviteResponse])
async def list_sysadmin_invites(
    response: Response,
    status: str | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    use_case: ListInvites = Depends(get_list_invites),
    invite_url_builder: InviteUrlBuilder = Depends(get_invite_url_builder),
    current_user: AuthenticatedUser = Depends(require_superuser),
):
    """
    Lista las invitaciones de sysadmin creadas en la plataforma.
    """
    invites, total = await use_case.execute(
        organization_id=None,
        is_sysadmin=True,
        role=None,
        status=status,
        page=page,
        page_size=page_size,
    )
    response.headers["X-Total-Count"] = str(total or 0)
    response.headers["X-Page-Size"] = str(page_size)
    response.headers["X-Page"] = str(page or 1)

    return [
        SysadminInviteResponse(
            id=invite.id,
            token=invite.token,
            email=invite.email,
            max_uses=invite.max_uses,
            uses=invite.uses,
            expires_at=invite.expires_at,
            invite_url=invite_url_builder.build(invite.token),
        )
        for invite in invites
    ]


@router.delete("/invites", response_model=DeleteInvitesResponse)
async def delete_sysadmin_invites(
    request: DeleteInvitesRequest,
    use_case: DeleteInvites = Depends(get_delete_invites),
    current_user: AuthenticatedUser = Depends(require_superuser),
):
    if not request.ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invite_ids_required",
        )

    deleted_count = await use_case.execute(
        ids=request.ids,
        is_sysadmin=True,
        organization_id=None,
    )
    return DeleteInvitesResponse(deleted_count=deleted_count)


@router.get("/sysadmins/stats", response_model=SysadminStatsResponse)
async def get_sysadmin_stats(
    use_case: ListSysadminsUseCase = Depends(get_list_sysadmins_use_case),
    current_user: AuthenticatedUser = Depends(require_superuser),
):
    stats = await use_case.get_stats()
    return SysadminStatsResponse(
        total_sysadmins=stats.total_sysadmins,
        active_sysadmins=stats.active_sysadmins,
        pending_invites=stats.pending_invites,
    )


@router.get("/sysadmins", response_model=list[SysadminUserResponse])
async def list_sysadmins(
    response: Response,
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    use_case: ListSysadminsUseCase = Depends(get_list_sysadmins_use_case),
    current_user: AuthenticatedUser = Depends(require_superuser),
):
    items, total = await use_case.list_sysadmins(
        search=search,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page-Size"] = str(page_size)
    response.headers["X-Page"] = str(page or 1)

    return [
        SysadminUserResponse(
            id=item.user.id,
            email=item.user.email,
            first_name=item.details.first_name if item.details else None,
            last_name=item.details.last_name if item.details else None,
            avatar_url=item.details.avatar_url if item.details else None,
            is_active=item.user.is_active,
        )
        for item in items
    ]


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_system_audit_logs(
    action: str | None = Query(default=None),
    organization_id: uuid.UUID | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    use_case: GetSystemAuditLogsUseCase = Depends(get_get_system_audit_logs_use_case),
    current_user: AuthenticatedUser = Depends(require_superuser),
):
    """
    Lista todos los registros de auditoría del sistema para administradores de plataforma.
    """
    result = await use_case.execute(
        action=action,
        organization_id=organization_id,
        user_id=user_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
    return AuditLogListResponse(
        items=[
            AuditLogItemResponse(
                id=item.id,
                user_id=item.user_id,
                user_email=item.user_email,
                user_name=item.user_name,
                organization_id=item.organization_id,
                action=item.action,
                resource_type=item.resource_type,
                resource_id=item.resource_id,
                details=item.details,
                created_at=item.created_at,
            )
            for item in result.items
        ],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        has_next=result.has_next,
    )
