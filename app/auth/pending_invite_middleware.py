from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.invites.cookies import clear_pending_invite_cookie


class PendingInviteCookieMiddleware(BaseHTTPMiddleware):
    """
    Si durante el request se marcó fallo de invitación, borra la cookie `pending_invite`
    en la respuesta (evita quedar con un token inválido colgado).
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if getattr(request.state, "clear_pending_invite_cookie", False):
            clear_pending_invite_cookie(response)
        return response
