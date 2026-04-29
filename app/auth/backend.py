from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from starlette.responses import RedirectResponse

from app.core import settings


class RedirectCookieTransport(CookieTransport):
    async def get_login_response(self, token: str):
        response = RedirectResponse(settings.frontend_post_login_url, status_code=303)
        return self._set_login_cookie(response, token)


cookie_transport = RedirectCookieTransport(
    cookie_name="auth",
    cookie_max_age=3600,
    cookie_secure=False,
    cookie_httponly=True,
    cookie_samesite="lax",
)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.auth_secret, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
