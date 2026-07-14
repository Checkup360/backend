import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
    BackgroundTasks,
)
from fastapi.security import OAuth2PasswordRequestForm
from app.application.interfaces import EmailSender
from app.application.dto import AuthenticatedUser
from app.application.use_cases.invitations import (
    DeleteInvites,
    InviteUrlBuilder,
    ListInvites,
)
from app.presentation.api.authorization import (
    require_organization_admin_or_sysadmin,
)
from app.infrastructure.authentication.machinery.backend import auth_backend
from app.infrastructure.authentication.machinery.users import fastapi_users
from app.infrastructure.authentication.manager import UserManager, get_user_manager
from app.infrastructure.authentication.machinery.cookies import (
    apply_pending_invite_cookie,
)
from app.presentation.api.responses import response_json
from app.domain.entities import Membership
from app.domain.exceptions import InviteError
from app.presentation.api.request_models import RedeemInviteBody, UserCreate
from app.presentation.api.request_models.invitations import (
    CreateOrganizationInviteRequest,
    DeleteInvitesRequest,
)
from app.presentation.api.response_models import (
    InviteRejected,
    PrepareGoogleSessionResponse,
)
from app.presentation.api.response_models.invitations import (
    CreateInviteResponse,
    DeleteInvitesResponse,
    InviteMetadataResponse,
    OrganizationInviteResponse,
    RedeemResponse,
)
from app.presentation.api.dependencies import (
    get_delete_invites,
    get_email_sender,
    get_invite_service,
    get_invite_url_builder,
    get_list_invites,
    get_organization_service,
    get_department_service,
)
from app.domain.services.invite import InviteService
from app.application.use_cases.organizations.organization_service import (
    OrganizationService,
)
from app.application.use_cases.departments.department_service import DepartmentService

from fastapi_users import exceptions
from fastapi_users.router.common import ErrorCode

router = APIRouter(prefix="/invites", tags=["invites"])


@router.post("/organization", response_model=CreateInviteResponse)
async def create_organization_invite(
    body: CreateOrganizationInviteRequest,
    background_tasks: BackgroundTasks,
    service: InviteService = Depends(get_invite_service),
    email_sender: EmailSender = Depends(get_email_sender),
    invite_url_builder: InviteUrlBuilder = Depends(get_invite_url_builder),
    org_service: OrganizationService = Depends(get_organization_service),
    dept_service: DepartmentService = Depends(get_department_service),
    admin_entity: Membership | AuthenticatedUser = Depends(
        require_organization_admin_or_sysadmin
    ),
):
    if isinstance(admin_entity, AuthenticatedUser):
        if not body.organization_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="organization_id_required_for_sysadmin",
            )
        org_id = body.organization_id
    else:
        org_id = admin_entity.organization_id

    try:
        invite = await service.create_invite(
            email=body.email,
            max_uses=body.max_uses,
            expires_in_hours=body.expires_in_hours,
            organization_id=org_id,
            department_id=body.department_id,
            role=body.role,
            is_sysadmin=False,
        )
    except InviteError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=e.code,
        )

    invite_url = invite_url_builder.build(invite.token)

    if body.email:
        organization_name = ""
        department_name = ""
        if org_id:
            org = await org_service.get_organization(org_id)
            if org:
                organization_name = org.name
        if body.department_id:
            try:
                dept_list = await dept_service.list_departments_as_superuser(org_id)
                dept = next((d for d in dept_list if d.id == body.department_id), None)
                if dept:
                    department_name = dept.name
            except Exception:
                pass

        background_tasks.add_task(
            email_sender.send_invite_email,
            to_email=body.email,
            invite_url=invite_url,
            is_sysadmin=False,
            role=body.role.value if hasattr(body.role, "value") else str(body.role),
            organization_name=organization_name,
            department_name=department_name,
        )

    return CreateInviteResponse(
        token=invite.token,
        invite_url=invite_url,
    )


@router.get("/organization", response_model=list[OrganizationInviteResponse])
async def list_organization_invites(
    response: Response,
    organization_id: uuid.UUID | None = Query(default=None),
    role: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int | None = Query(default=None, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    use_case: ListInvites = Depends(get_list_invites),
    invite_url_builder: InviteUrlBuilder = Depends(get_invite_url_builder),
    admin_entity: Membership | AuthenticatedUser = Depends(
        require_organization_admin_or_sysadmin
    ),
):
    if isinstance(admin_entity, AuthenticatedUser):
        org_id = organization_id
    else:
        org_id = admin_entity.organization_id

    invites, total = await use_case.execute(
        organization_id=org_id,
        is_sysadmin=False,
        role=role,
        status=status,
        page=page,
        page_size=page_size,
    )
    response.headers["X-Total-Count"] = str(total or 0)
    response.headers["X-Page-Size"] = str(page_size)
    response.headers["X-Page"] = str(page or 1)

    return [
        OrganizationInviteResponse(
            id=invite.id,
            token=invite.token,
            email=invite.email,
            role=invite.role.value if invite.role else None,
            organization_id=invite.organization_id,
            organization_name=(
                invite.organization.name if invite.organization else None
            ),
            department_id=invite.department_id,
            department_name=invite.department.name if invite.department else None,
            max_uses=invite.max_uses,
            uses=invite.uses,
            expires_at=invite.expires_at,
            invite_url=invite_url_builder.build(invite.token),
        )
        for invite in invites
    ]


@router.delete("/organization", response_model=DeleteInvitesResponse)
async def delete_organization_invites(
    body: DeleteInvitesRequest,
    use_case: DeleteInvites = Depends(get_delete_invites),
    admin_entity: Membership | AuthenticatedUser = Depends(
        require_organization_admin_or_sysadmin
    ),
):
    if not body.ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="invite_ids_required",
        )

    organization_id = (
        None
        if isinstance(admin_entity, AuthenticatedUser)
        else admin_entity.organization_id
    )
    deleted_count = await use_case.execute(
        ids=body.ids,
        is_sysadmin=False,
        organization_id=organization_id,
    )
    return DeleteInvitesResponse(deleted_count=deleted_count)


@router.get("/{token}", response_model=InviteMetadataResponse)
async def get_invite_metadata(
    token: str,
    service: InviteService = Depends(get_invite_service),
):
    invite = await service.check_invite_usable(token)
    return InviteMetadataResponse(
        organization_id=invite.organization_id,
        organization_name=invite.organization.name if invite.organization else None,
        role=invite.role.value if invite.role else None,
        is_sysadmin=invite.is_sysadmin,
    )


@router.post(
    "/{token}/google-session",
    response_model=PrepareGoogleSessionResponse,
    responses={400: {"model": InviteRejected}},
)
async def prepare_google_registration(
    token: str,
    request: Request,
    service: InviteService = Depends(get_invite_service),
) -> Response:
    try:
        await service.check_invite_usable(token)
    except InviteError as e:
        request.state.clear_pending_invite_cookie = True
        return response_json(InviteRejected(code=e.code), status_code=400)

    ok = PrepareGoogleSessionResponse(ok=True)
    r = response_json(ok, status_code=200)
    apply_pending_invite_cookie(r, token)
    return r


@router.post("/{token}/redeem")
async def redeem_invite(
    token: str,
    body: RedeemInviteBody,
    request: Request,
    user_manager: UserManager = Depends(get_user_manager),
    invite_service: InviteService = Depends(get_invite_service),
    strategy=Depends(auth_backend.get_strategy),
    current_user=Depends(fastapi_users.current_user(optional=True, active=True)),
):
    if current_user:
        email = current_user.email
    else:
        if not body.email or not body.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email and password are required",
            )
        email = body.email

    try:
        invite = await invite_service.validate_invite(token, email)
    except InviteError as e:
        request.state.clear_pending_invite_cookie = True
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=InviteRejected(code=e.code).model_dump(),
        )

    if current_user:
        await invite_service.consume_invite(invite.id, current_user.id)
        return RedeemResponse()

    email = body.email
    password = body.password
    if email is None or password is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required",
        )

    existing = await user_manager.user_db.get_by_email(email)
    if existing:
        credentials = OAuth2PasswordRequestForm(username=email, password=password)
        user = await user_manager.authenticate(credentials)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorCode.LOGIN_BAD_CREDENTIALS,
            )
        await invite_service.consume_invite(invite.id, user.id)
        response = await auth_backend.login(strategy, user)
        await user_manager.on_after_login(user, request, response)
        return response

    request.state.invite_token_override = token
    request.state.invite_validation_error_as_json = True
    user_create = UserCreate(email=email, password=password)
    try:
        user = await user_manager.create(user_create, safe=True, request=request)
    except exceptions.InvalidPasswordException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": ErrorCode.REGISTER_INVALID_PASSWORD,
                "reason": e.reason,
            },
        )

    response = await auth_backend.login(strategy, user)
    await user_manager.on_after_login(user, request, response)
    return response
