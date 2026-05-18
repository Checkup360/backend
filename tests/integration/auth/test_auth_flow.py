import pytest
from sqlalchemy import select

from app.core import settings
from app.persistence.models import Membership, Organization, User
from app.domain.entities.org_role import OrgRole


def redeem(client, token: str, email: str, password: str = "SuperSecure123!"):
    return client.post(
        f"/invites/{token}/redeem",
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

        response = redeem(client, invite.token, "juan@example.com")

        assert response.status_code == 303

        me_response = client.get("/auth/me")
        assert me_response.status_code == 200
        data = me_response.json()
        assert data["email"] == "juan@example.com"
        assert data["is_sysadmin"] is False
        assert data["memberships"] == []
        assert data["requires_onboarding"] is False

    @pytest.mark.asyncio
    async def test_with_expired_invite(self, client, make_invite):
        invite = await make_invite(
            token="expired-invite",
            email="juan@example.com",
            expires_in_hours=-1,
        )

        response = redeem(client, invite.token, "juan@example.com")

        assert_error_code(response, "invite_expired")

    @pytest.mark.asyncio
    async def test_with_used_invite(self, client, make_invite):
        invite = await make_invite(
            token="used-invite",
            email="juan@example.com",
            uses=1,
        )

        redeem(client, invite.token, "juan@example.com")
        response = redeem(client, invite.token, "fede@example.com")

        assert_error_code(response, "invite_used")

    @pytest.mark.asyncio
    async def test_with_email_mismatch(self, client, make_invite):
        invite = await make_invite(
            token="invite-juan",
            email="juan@example.com",
            expires_in_hours=1,
        )

        response = redeem(client, invite.token, "otro@example.com")

        assert_error_code(response, "email_mismatch")

    @pytest.mark.asyncio
    async def test_with_nonexistent_invite(self, client):
        response = redeem(client, "nonexistent-token", "juan@example.com")

        assert_error_code(response, "invalid_invite")


class TestMeEndpoint:
    def test_without_auth(self, client):
        response = client.get("/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_with_auth_returns_expanded_response(self, client, make_invite):
        invite = await make_invite(
            token="me-basic-invite",
            email="juan@example.com",
            expires_in_hours=1,
        )
        redeem(client, invite.token, "juan@example.com")
        response = client.get("/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "juan@example.com"
        assert data["is_sysadmin"] is False
        assert data["memberships"] == []
        assert data["requires_onboarding"] is False

    @pytest.mark.asyncio
    async def test_sysadmin_returns_is_sysadmin_true(
        self, client, make_invite, db_session_maker
    ):
        invite = await make_invite(
            token="me-sysadmin-invite",
            email="admin@example.com",
            expires_in_hours=1,
        )
        redeem(client, invite.token, "admin@example.com")
        async with db_session_maker() as session:
            user = await session.scalar(
                select(User).where(User.email == "admin@example.com")
            )
            user.is_superuser = True
            await session.commit()
        response = client.get("/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["is_sysadmin"] is True
        assert data["requires_onboarding"] is False

    @pytest.mark.asyncio
    async def test_user_with_org_membership_returns_memberships(
        self, client, make_invite, db_session_maker
    ):
        invite = await make_invite(
            token="me-membership-invite",
            email="user@example.com",
            expires_in_hours=1,
        )
        redeem(client, invite.token, "user@example.com")

        async with db_session_maker() as session:
            user = await session.scalar(
                select(User).where(User.email == "user@example.com")
            )
            org = Organization(name="Test Org", slug="test-org-me")
            session.add(org)
            await session.flush()
            session.add(
                Membership(
                    user_id=user.id,
                    organization_id=org.id,
                    role=OrgRole.ADMIN,
                )
            )
            await session.commit()

        response = client.get("/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert len(data["memberships"]) == 1
        assert data["memberships"][0]["organization_id"] == str(org.id)
        assert data["memberships"][0]["organization_name"] == "Test Org"
        assert data["memberships"][0]["role"] == "admin"
        assert data["requires_onboarding"] is False


class TestLoginEndpoint:
    @pytest.mark.asyncio
    async def test_login_returns_redirect_and_auth_cookie(self, client, make_invite):
        invite = await make_invite(
            token="login-invite-123",
            email="juan@example.com",
            expires_in_hours=1,
        )

        redeem(client, invite.token, "juan@example.com")
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
        data = me_response.json()
        assert data["email"] == "juan@example.com"
        assert data["is_sysadmin"] is False
        assert data["memberships"] == []
        assert data["requires_onboarding"] is False
