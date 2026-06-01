import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from starlette.responses import Response

from app.auth.authorization import require_organization_admin_or_sysadmin
from app.auth.machinery.backend import auth_backend
from app.auth.machinery.users import fastapi_users
from app.auth.manager import UserManager, get_user_manager
from app.auth.machinery.cookies import apply_pending_invite_cookie
from app.core.responses import response_json
from app.domain.entities import Membership
from app.persistence.models import User
from app.domain.entities.org_role import OrgRole
from app.domain.exceptions import InviteError
from app.schemas.invite import (
    InviteRejected,
    PrepareGoogleSessionResponse,
    RedeemInviteBody,
)
from app.schemas.user import UserCreate
from app.dependencies import get_invite_service
from app.domain.services.invite import InviteService, build_invite_url

from fastapi_users import exceptions
from fastapi_users.router.common import ErrorCode

router = APIRouter(prefix="/invites", tags=["invites"])


class OrganizationInviteResponse(BaseModel):
    id: uuid.UUID
    token: str
    email: str | None = None
    role: str | None = None
    organization_id: uuid.UUID | None = None
    organization_name: str | None = None
    department_id: uuid.UUID | None = None
    department_name: str | None = None
    max_uses: int
    uses: int
    expires_at: datetime
    invite_url: str


class CreateOrganizationInviteRequest(BaseModel):
    email: str | None = None
    expires_in_hours: int = 24
    max_uses: int = 1
    organization_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    role: OrgRole


class CreateInviteResponse(BaseModel):
    token: str
    invite_url: str


class InviteMetadataResponse(BaseModel):
    organization_id: uuid.UUID | None = None
    organization_name: str | None = None
    role: str | None = None
    is_sysadmin: bool = False


class RedeemResponse(BaseModel):
    ok: bool = True


@router.post("/organization", response_model=CreateInviteResponse)
async def create_organization_invite(
    body: CreateOrganizationInviteRequest,
    service: InviteService = Depends(get_invite_service),
    admin_entity: Membership | User = Depends(require_organization_admin_or_sysadmin),
):
    if isinstance(admin_entity, User):
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

    return CreateInviteResponse(
        token=invite.token,
        invite_url=build_invite_url(invite.token),
    )


@router.get("/organization", response_model=list[OrganizationInviteResponse])
async def list_organization_invites(
    organization_id: uuid.UUID | None = Query(default=None),
    role: str | None = Query(default=None),
    service: InviteService = Depends(get_invite_service),
    admin_entity: Membership | User = Depends(require_organization_admin_or_sysadmin),
):
    if isinstance(admin_entity, User):
        org_id = organization_id
    else:
        org_id = admin_entity.organization_id

    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from app.persistence.models.invite import InviteToken as InviteTokenORM
    from app.persistence.models.membership import OrgRole

    query = select(InviteTokenORM).options(
        selectinload(InviteTokenORM.department),
        selectinload(InviteTokenORM.organization),
    )
    if org_id is not None:
        query = query.where(InviteTokenORM.organization_id == org_id)
    else:
        query = query.where(InviteTokenORM.is_sysadmin.is_(False))

    if role is not None:
        try:
            query = query.where(InviteTokenORM.role == OrgRole(role.lower()))
        except ValueError:
            pass

    query = query.order_by(InviteTokenORM.created_at.desc())
    result = await service.invite_repo.db.scalars(query)
    orms = result.all()

    return [
        OrganizationInviteResponse(
            id=orm.id,
            token=orm.token,
            email=orm.email,
            role=orm.role.value if orm.role else None,
            organization_id=orm.organization_id,
            organization_name=orm.organization.name if orm.organization else None,
            department_id=orm.department_id,
            department_name=orm.department.name if orm.department else None,
            max_uses=orm.max_uses,
            uses=orm.uses,
            expires_at=orm.expires_at,
            invite_url=build_invite_url(orm.token),
        )
        for orm in orms
    ]


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

    existing = await user_manager.user_db.get_by_email(body.email)
    if existing:
        credentials = OAuth2PasswordRequestForm(
            username=body.email, password=body.password
        )
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
    user_create = UserCreate(email=body.email, password=body.password)
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
