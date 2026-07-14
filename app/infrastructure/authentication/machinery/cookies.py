"""Cookie `pending_invite` (flujo OAuth con invitación)."""

from starlette.responses import Response

from app.infrastructure.config import settings

PENDING_INVITE_COOKIE = "pending_invite"


def apply_pending_invite_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=PENDING_INVITE_COOKIE,
        value=token,
        max_age=600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_pending_invite_cookie(response: Response) -> None:
    response.delete_cookie(
        key=PENDING_INVITE_COOKIE,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
