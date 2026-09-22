from typing import Optional
from urllib.parse import urlparse

from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

from app.infrastructure.config import settings


class RedirectCookieTransport(CookieTransport):
    async def get_login_response(self, token: str):
        response = RedirectResponse(settings.frontend_post_login_url, status_code=303)
        return self._set_login_cookie(response, token)

    def _resolve_refresh_path(self, request: Optional[Request] = None) -> str:
        if request:
            prefix = request.headers.get("x-forwarded-prefix", "").rstrip("/")
            if prefix:
                return f"{prefix}/auth"
        return "/auth"

    def _set_refresh_cookie(
        self,
        response: Response,
        refresh_token: str,
        request: Optional[Request] = None,
    ) -> Response:
        path = self._resolve_refresh_path(request)
        response.set_cookie(
            settings.refresh_token_cookie_name,
            refresh_token,
            max_age=settings.refresh_token_lifetime_seconds,
            path=path,
            domain=self.cookie_domain,
            secure=self.cookie_secure,
            httponly=self.cookie_httponly,
            samesite=self.cookie_samesite,
        )
        return response

    def _set_logout_cookie(
        self,
        response: Response,
        request: Optional[Request] = None,
    ) -> Response:
        super()._set_logout_cookie(response)
        paths = {"/api/auth", "/auth"}
        if request:
            paths.add(self._resolve_refresh_path(request))
        for path in sorted(paths):
            response.set_cookie(
                settings.refresh_token_cookie_name,
                "",
                max_age=0,
                path=path,
                domain=self.cookie_domain,
                secure=self.cookie_secure,
                httponly=self.cookie_httponly,
                samesite=self.cookie_samesite,
            )
        return response


# Derive cookie domain from frontend_url to allow subdomains to share session
parsed_url = urlparse(settings.frontend_url)
cookie_domain = parsed_url.hostname
if cookie_domain in ("localhost", "127.0.0.1") or (
    cookie_domain and cookie_domain.replace(".", "").isdigit()
):
    cookie_domain = None


cookie_transport = RedirectCookieTransport(
    cookie_name="auth",
    cookie_max_age=settings.access_token_lifetime_seconds,
    cookie_secure=settings.cookie_secure,
    cookie_httponly=True,
    cookie_samesite="lax",
    cookie_domain=cookie_domain,
)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.auth_secret,
        lifetime_seconds=settings.access_token_lifetime_seconds,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
