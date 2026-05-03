import pytest
from types import SimpleNamespace

from app.core import settings


def register(client, token: str, email: str, password: str = "SuperSecure123!"):
    return client.post(
        f"/invites/{token}/register",
        json={"email": email, "password": password},
        follow_redirects=False,
    )


def assert_error_code(response, code: str, status_code: int = 400):
    assert response.status_code == status_code
    assert response.json()["detail"]["code"] == code


class TestRegister:
    @pytest.mark.asyncio
    async def test_with_valid_invite(self, client, make_invite):
        invite = await make_invite(
            token="valid-invite-123",
            email="juan@example.com",
            expires_in_hours=1,
        )

        response = register(client, invite.token, "juan@example.com")

        assert response.status_code == 303

        me_response = client.get("/auth/me")
        assert me_response.status_code == 200
        assert me_response.json() == {"email": "juan@example.com"}

    @pytest.mark.asyncio
    async def test_with_expired_invite(self, client, make_invite):
        invite = await make_invite(
            token="expired-invite",
            email="juan@example.com",
            expires_in_hours=-1,
        )

        response = register(client, invite.token, "juan@example.com")

        assert_error_code(response, "invite_expired")

    @pytest.mark.asyncio
    async def test_with_used_invite(self, client, make_invite):
        invite = await make_invite(
            token="used-invite",
            email="juan@example.com",
            used=False,
        )

        register(client, invite.token, "juan@example.com")
        response = register(client, invite.token, "fede@example.com")

        assert_error_code(response, "invite_used")

    @pytest.mark.asyncio
    async def test_with_email_mismatch(self, client, make_invite):
        invite = await make_invite(
            token="invite-juan",
            email="juan@example.com",
            expires_in_hours=1,
        )

        response = register(client, invite.token, "otro@example.com")

        assert_error_code(response, "email_mismatch")

    @pytest.mark.asyncio
    async def test_with_nonexistent_invite(self, client):
        response = register(client, "nonexistent-token", "juan@example.com")

        assert_error_code(response, "invalid_invite")


class TestMeEndpoint:
    def test_without_auth(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_with_auth(self, client, override_current_user):
        override_current_user(SimpleNamespace(email="juan@example.com"))

        response = client.get("/auth/me")
        assert response.status_code == 200
        assert response.json() == {"email": "juan@example.com"}


class TestLoginEndpoint:
    @pytest.mark.asyncio
    async def test_login_returns_redirect_and_auth_cookie(self, client, make_invite):
        invite = await make_invite(
            token="login-invite-123",
            email="juan@example.com",
            expires_in_hours=1,
        )

        register(client, invite.token, "juan@example.com")
        client.cookies.clear()

        response = client.post(
            "/auth/login",
            data={"username": "juan@example.com", "password": "SuperSecure123!"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == settings.frontend_post_login_url

        me_response = client.get("/auth/me")
        assert me_response.status_code == 200
        assert me_response.json() == {"email": "juan@example.com"}
