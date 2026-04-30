from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.responses import Response

from app.auth.backend import auth_backend
from app.auth.manager import UserManager, get_user_manager
from app.invites.cookies import apply_pending_invite_cookie
from app.invites.json_response import response_json
from app.invites.service import fetch_usable_invite
from app.schemas.invite import (
    InvitePasswordRegisterBody,
    InviteRejected,
    PrepareGoogleSessionResponse,
)
from app.schemas.user import UserCreate

from fastapi_users import exceptions
from fastapi_users.router.common import ErrorCode

router = APIRouter(prefix="/invites", tags=["invites"])


@router.post(
    "/{token}/google-session",
    response_model=PrepareGoogleSessionResponse,
    responses={400: {"model": InviteRejected}},
)
async def prepare_google_registration(token: str, request: Request) -> Response:
    """
    Valida el invite y setea la cookie `pending_invite` para el callback OAuth.
    Si el invite no sirve, responde 400 tipado y se limpia cualquier cookie vieja.
    """
    db = request.state.db
    _, err = await fetch_usable_invite(db, token)
    if err:
        request.state.clear_pending_invite_cookie = True
        return response_json(InviteRejected(code=err), status_code=400)

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
    """
    Registro con email/contraseña; el token de invitación va solo en la URL.
    La validez y el consumo del invite los hace UserManager.create.
    """
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
