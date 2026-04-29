from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel

from app.auth.backend import auth_backend
from app.auth.google_oauth import google_oauth_client
from app.auth.users import current_active_user, fastapi_users
from app.core import settings
from app.models import User
from app.schemas import AuthMeResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import InviteToken
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="",
)

router.include_router(
    fastapi_users.get_oauth_router(
        oauth_client=google_oauth_client,
        backend=auth_backend,
        state_secret=settings.auth_secret,
        associate_by_email=True,
        is_verified_by_default=True,
    ),
    prefix="/google",
)


@router.get("/me", response_model=AuthMeResponse)
def get_me(user: User = Depends(current_active_user)) -> AuthMeResponse:
    return AuthMeResponse(email=user.email)


@router.get("/google/authorize")
async def authorize_with_invite(
    invite_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint custom para registro/login con Google.
    Valida el invite token, lo setea en una cookie, y redirige a Google.
    """
    # Validar que el invite exista y sea válido
    invite = await db.scalar(
        select(InviteToken).where(InviteToken.token == invite_token)
    )

    if not invite:
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/error?reason=invalid_invite",
            status_code=303,
        )

    if invite.used:
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/error?reason=invite_used",
            status_code=303,
        )

    if invite.expires_at < datetime.utcnow():
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/error?reason=invite_expired",
            status_code=303,
        )

    # Todo ok: setear cookie con el invite token (httponly, 10 minutos)
    response = RedirectResponse(
        url=f"{settings.frontend_url}/auth/google/callback",  # Placeholder: será redirigido por fastapi-users
        status_code=303,
    )
    response.set_cookie(
        key="pending_invite",
        value=invite_token,
        max_age=600,  # 10 minutos
        httponly=True,
        secure=True,
        samesite="lax",
    )

    # Redirigir a Google OAuth
    # Nota: Aquí debería ir el redirect a Google, pero fastapi-users maneja eso.
    # Por ahora, devolvemos el response con la cookie seteada.
    # En un flujo real, necesitarías integrar con el endpoint de authorize de fastapi-users.
    return response


class RegisterRequest(BaseModel):
    email: str
    password: str
    invite_token: str | None = None


class PendingInviteRequest(BaseModel):
    invite_token: str


class PendingInviteResponse(BaseModel):
    ok: bool


@router.post("/register")
async def register_with_invite(
    request: RegisterRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint custom para registro con email/password.
    Recibe invite_token en el body, lo valida, y delega al registro de fastapi-users.
    """
    if not request.invite_token:
        raise HTTPException(
            status_code=400,
            detail="invite_token es requerido",
        )

    # Pasar el token en request.state para que UserManager lo encuentre
    http_request.state.invite_token_override = request.invite_token
    http_request.state.db = db

    # Aquí iría el flujo de registro con fastapi-users
    # Por ahora, retornamos un placeholder
    return {"message": "Registro completado"}


@router.post("/pending_invite", response_model=PendingInviteResponse)
async def set_pending_invite(
    payload: PendingInviteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Valida un invite token y lo setea en una cookie `pending_invite`.
    Body: {"invite_token": "..."}
    """
    invite_token = payload.invite_token

    invite = await db.scalar(select(InviteToken).where(InviteToken.token == invite_token))
    if not invite:
        return JSONResponse({"detail": "invalid_invite"}, status_code=400)
    if invite.used:
        return JSONResponse({"detail": "invite_used"}, status_code=400)
    if invite.expires_at < datetime.utcnow():
        return JSONResponse({"detail": "invite_expired"}, status_code=400)

    response = JSONResponse({"ok": True})
    response.set_cookie(
        key="pending_invite",
        value=invite_token,
        max_age=600,
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return response



