from urllib.parse import urlparse

from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from starlette.responses import RedirectResponse

from app.infrastructure.config import settings


class RedirectCookieTransport(CookieTransport):
    async def get_login_response(self, token: str):
        response = RedirectResponse(settings.frontend_post_login_url, status_code=303)
        return self._set_login_cookie(response, token)


# Derive cookie domain from frontend_url to allow subdomains to share session
parsed_url = urlparse(settings.frontend_url)
cookie_domain = parsed_url.hostname
if cookie_domain in ("localhost", "127.0.0.1") or (
    cookie_domain and cookie_domain.replace(".", "").isdigit()
):
    cookie_domain = None


cookie_transport = RedirectCookieTransport(
    cookie_name="auth",
    cookie_max_age=3600,
    cookie_secure=settings.cookie_secure,
    cookie_httponly=True,
    cookie_samesite="lax",
    cookie_domain=cookie_domain,
)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.auth_secret, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
