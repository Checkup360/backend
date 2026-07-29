import pytest
from app.infrastructure.authentication.machinery.backend import (
    get_jwt_strategy,
    auth_backend,
    cookie_transport,
    RedirectCookieTransport,
)


def test_get_jwt_strategy():
    strategy = get_jwt_strategy()
    assert strategy is not None


def test_auth_backend_configuration():
    assert auth_backend.name == "jwt"
    assert auth_backend.transport == cookie_transport


@pytest.mark.asyncio
async def test_redirect_cookie_transport_get_login_response():
    transport = RedirectCookieTransport(
        cookie_name="auth",
        cookie_max_age=3600,
        cookie_secure=False,
        cookie_httponly=True,
        cookie_samesite="lax",
    )
    response = await transport.get_login_response("sample-jwt-token")
    assert response.status_code == 303
    assert "set-cookie" in response.headers
