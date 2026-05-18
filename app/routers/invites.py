import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from starlette.responses import Response

from app.auth.authorization import require_organization_admin_or_sysadmin
from app.auth.machinery.backend import auth_backend
from app.auth.manager import UserManager, get_user_manager
from app.auth.machinery.cookies import apply_pending_invite_cookie
from app.core.responses import response_json
from app.domain.entities import Membership
from app.domain.entities.org_role import OrgRole
from app.domain.exceptions import InviteError
from app.schemas.invite import (
    InvitePasswordRegisterBody,
    InviteRejected,
    PrepareGoogleSessionResponse,
)
from app.schemas.user import UserCreate
from app.dependencies import get_invite_service
from app.domain.services.invite import InviteService, build_invite_url

from fastapi_users import exceptions
from fastapi_users.router.common import ErrorCode

router = APIRouter(prefix="/invites", tags=["invites"])


class CreateOrganizationInviteRequest(BaseModel):
    email: str | None = None
    expires_in_hours: int = 24
    max_uses: int = 1
    organization_id: uuid.UUID
    role: OrgRole


class CreateInviteResponse(BaseModel):
    token: str
    invite_url: str


@router.post("/organization", response_model=CreateInviteResponse)
async def create_organization_invite(
    body: CreateOrganizationInviteRequest,
    service: InviteService = Depends(get_invite_service),
    _: Membership | None = Depends(require_organization_admin_or_sysadmin),
):
    invite = await service.create_invite(
        email=body.email,
        max_uses=body.max_uses,
        expires_in_hours=body.expires_in_hours,
        organization_id=body.organization_id,
        role=body.role,
        is_sysadmin=False,
    )

    return CreateInviteResponse(
        token=invite.token,
        invite_url=build_invite_url(invite.token),
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


@router.post("/{token}/register")
async def register_with_invite_token(
    token: str,
    body: InvitePasswordRegisterBody,
    request: Request,
    user_manager: UserManager = Depends(get_user_manager),
    strategy=Depends(auth_backend.get_strategy),
):
    request.state.invite_token_override = token
    request.state.invite_validation_error_as_json = True

    user_create = UserCreate(email=body.email, password=body.password)
    try:
        user = await user_manager.create(user_create, safe=True, request=request)
    except exceptions.UserAlreadyExists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorCode.REGISTER_USER_ALREADY_EXISTS,
        )
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
