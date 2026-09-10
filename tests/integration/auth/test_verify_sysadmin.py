import pytest


class TestVerifySysadmin:
    def test_unauthenticated_request_is_rejected(self, client):
        response = client.get("/auth/verify-sysadmin")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_non_sysadmin_user_is_forbidden(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="regular_user@example.com",
            is_superuser=False,
        )
        response = client.get("/auth/verify-sysadmin")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_sysadmin_user_is_allowed(self, client, auth_scenario):
        admin_email = "admin_user@example.com"
        await auth_scenario.register_and_login(
            email=admin_email,
            is_superuser=True,
        )
        response = client.get("/auth/verify-sysadmin")
        assert response.status_code == 200
        assert response.headers.get("remote-user") == admin_email
        assert response.headers.get("remote-email") == admin_email
