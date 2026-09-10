import pytest


class TestAdminSysadminsEndpoints:
    def test_unauthenticated_request_is_rejected(self, client):
        res = client.get("/admin/sysadmins")
        assert res.status_code == 401
        res_stats = client.get("/admin/sysadmins/stats")
        assert res_stats.status_code == 401

    @pytest.mark.asyncio
    async def test_non_sysadmin_is_forbidden(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="regular_employee@example.com",
            is_superuser=False,
        )
        res = client.get("/admin/sysadmins")
        assert res.status_code == 403
        res_stats = client.get("/admin/sysadmins/stats")
        assert res_stats.status_code == 403

    @pytest.mark.asyncio
    async def test_sysadmin_can_list_sysadmins_and_stats(self, client, auth_scenario):
        admin_email = "super_admin@example.com"
        await auth_scenario.register_and_login(
            email=admin_email,
            is_superuser=True,
        )
        res_stats = client.get("/admin/sysadmins/stats")
        assert res_stats.status_code == 200
        stats = res_stats.json()
        assert stats["total_sysadmins"] >= 1
        assert stats["active_sysadmins"] >= 1
        assert "pending_invites" in stats

        res = client.get("/admin/sysadmins")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(item["email"] == admin_email for item in data)
        assert res.headers.get("X-Total-Count") is not None
