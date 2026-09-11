import pytest
from urllib.parse import parse_qs, urlparse

from app.infrastructure.config import settings
from app.infrastructure.email import SmtpEmailSender


def redeem(client, token: str, email: str, password: str = "SuperSecure123!"):
    return client.post(
        f"/invites/{token}/redeem",
        json={"email": email, "password": password},
        follow_redirects=False,
    )


class TestRefreshFlow:
    @pytest.mark.asyncio
    async def test_login_sets_refresh_token_cookie(self, client, make_invite):
        invite = await make_invite(
            token="refresh-test-invite-1",
            email="testuser@example.com",
            expires_in_hours=1,
        )
        redeem(client, invite.token, "testuser@example.com")
        client.cookies.clear()

        response = client.post(
            "/auth/login",
            data={"username": "testuser@example.com", "password": "SuperSecure123!"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert "auth" in client.cookies
        assert settings.refresh_token_cookie_name in client.cookies
        assert client.cookies[settings.refresh_token_cookie_name] is not None

    @pytest.mark.asyncio
    async def test_refresh_token_success_and_rotation(self, client, make_invite):
        invite = await make_invite(
            token="refresh-test-invite-2",
            email="testuser2@example.com",
            expires_in_hours=1,
        )
        redeem(client, invite.token, "testuser2@example.com")
        client.cookies.clear()

        login_resp = client.post(
            "/auth/login",
            data={"username": "testuser2@example.com", "password": "SuperSecure123!"},
            follow_redirects=False,
        )
        assert login_resp.status_code == 303
        old_refresh_token = client.cookies.get(settings.refresh_token_cookie_name)

        # Simulate access token expiration by removing "auth" cookie
        del client.cookies["auth"]

        # /auth/me should fail now because access token is missing
        unauth_resp = client.get("/auth/me")
        assert unauth_resp.status_code == 401

        # Now call /auth/refresh using the refresh_token cookie
        refresh_resp = client.post("/auth/refresh")
        assert refresh_resp.status_code == 200
        assert refresh_resp.json() == {"ok": True}

        new_access_token = client.cookies.get("auth")
        new_refresh_token = client.cookies.get(settings.refresh_token_cookie_name)

        assert new_access_token is not None
        assert new_refresh_token is not None
        assert new_refresh_token != old_refresh_token

        # /auth/me should succeed again
        me_resp = client.get("/auth/me")
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == "testuser2@example.com"

        # Attempting to use the OLD refresh token must fail (it was rotated)
        client.cookies[settings.refresh_token_cookie_name] = old_refresh_token
        reuse_resp = client.post("/auth/refresh")
        assert reuse_resp.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_without_cookie_fails(self, client):
        client.cookies.clear()
        response = client.post("/auth/refresh")
        assert response.status_code == 401
        assert "Missing refresh token" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_logout_clears_cookies_and_revokes(self, client, make_invite):
        invite = await make_invite(
            token="refresh-test-invite-3",
            email="testuser3@example.com",
            expires_in_hours=1,
        )
        redeem(client, invite.token, "testuser3@example.com")
        client.cookies.clear()

        client.post(
            "/auth/login",
            data={"username": "testuser3@example.com", "password": "SuperSecure123!"},
            follow_redirects=False,
        )
        refresh_tok = client.cookies.get(settings.refresh_token_cookie_name)
        assert refresh_tok is not None

        # Call /auth/logout
        logout_resp = client.post("/auth/logout")
        assert logout_resp.status_code == 204

        # Both cookies should now be deleted / empty
        assert client.cookies.get("auth") is None or client.cookies.get("auth") == ""
        assert (
            client.cookies.get(settings.refresh_token_cookie_name) is None
            or client.cookies.get(settings.refresh_token_cookie_name) == ""
        )

        # Using the logged-out refresh token directly must fail
        client.cookies[settings.refresh_token_cookie_name] = refresh_tok
        revoked_refresh = client.post("/auth/refresh")
        assert revoked_refresh.status_code == 401

    @pytest.mark.asyncio
    async def test_password_reset_revokes_refresh_tokens(
        self, client, make_invite, monkeypatch
    ):
        invite = await make_invite(
            token="refresh-pwd-invite",
            email="reset-refresh@example.com",
            expires_in_hours=1,
        )
        redeem(client, invite.token, "reset-refresh@example.com")
        client.cookies.clear()

        client.post(
            "/auth/login",
            data={
                "username": "reset-refresh@example.com",
                "password": "SuperSecure123!",
            },
            follow_redirects=False,
        )
        active_refresh_token = client.cookies.get(settings.refresh_token_cookie_name)
        assert active_refresh_token is not None

        # Perform password reset flow
        sent_urls: list[str] = []

        def capture_reset_email(self, to_email: str, reset_url: str) -> None:
            assert to_email == "reset-refresh@example.com"
            sent_urls.append(reset_url)

        monkeypatch.setattr(
            SmtpEmailSender,
            "send_password_reset_email",
            capture_reset_email,
        )

        client.post(
            "/auth/forgot-password",
            json={"email": "reset-refresh@example.com"},
        )
        assert len(sent_urls) == 1
        reset_token = parse_qs(urlparse(sent_urls[0]).query)["token"][0]

        reset_resp = client.post(
            "/auth/reset-password",
            json={"token": reset_token, "password": "BrandNewPassword123!"},
        )
        assert reset_resp.status_code == 200

        # The old refresh token should now be revoked
        client.cookies[settings.refresh_token_cookie_name] = active_refresh_token
        refresh_after_reset = client.post("/auth/refresh")
        assert refresh_after_reset.status_code == 401
