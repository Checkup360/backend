import pytest


class TestAdminRouter:
    @pytest.mark.asyncio
    async def test_list_sysadmin_invites_with_pagination_and_status(
        self, client, make_invite, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="sysadmin-list@example.com",
            is_superuser=True,
        )
        inv1 = await make_invite(
            email="inv1@example.com",
            is_sysadmin=True,
        )
        inv2 = await make_invite(
            email="inv2@example.com",
            is_sysadmin=True,
            uses=1,
            max_uses=1,
        )

        # list all
        res = client.get("/admin/invites?page=1&page_size=10")
        assert res.status_code == 200
        assert "X-Total-Count" in res.headers
        assert res.headers["X-Page"] == "1"
        assert res.headers["X-Page-Size"] == "10"
        items = res.json()
        assert any(i["id"] == str(inv1.id) for i in items)

        # list with status filter "active"
        res_active = client.get("/admin/invites?status=active")
        assert res_active.status_code == 200
        active_items = res_active.json()
        assert any(i["id"] == str(inv1.id) for i in active_items)

        # list with status filter "used"
        res_used = client.get("/admin/invites?status=used")
        assert res_used.status_code == 200
        used_items = res_used.json()
        assert any(i["id"] == str(inv2.id) for i in used_items)

    @pytest.mark.asyncio
    async def test_delete_sysadmin_invites_empty_ids_validation_error(
        self, client, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="sysadmin-del-empty@example.com",
            is_superuser=True,
        )

        res = client.request(
            "DELETE",
            "/admin/invites",
            json={"ids": []},
        )
        assert res.status_code == 422
        assert res.json()["detail"] == "invite_ids_required"
