import pytest

from app.domain.value_objects.org_role import OrgRole


class TestOrganizationLogoAndNameFlow:
    @pytest.mark.asyncio
    async def test_update_name_and_logo_flow(self, client, auth_scenario):
        user = await auth_scenario.register_and_login(
            email="orgadmin-logo@example.com",
            memberships=[("initial-org", OrgRole.ADMIN)],
        )
        org_id = user.membership.organization_id

        # 1. Get organization details
        get_res = client.get(f"/organizations/{org_id}")
        assert get_res.status_code == 200
        assert get_res.json()["name"] == "Initial Org"
        assert get_res.json()["logo_url"] is None

        # 2. Update organization name
        patch_res = client.patch(
            f"/organizations/{org_id}",
            json={"name": "Renamed Healthcare Corp"},
        )
        assert patch_res.status_code == 200
        assert patch_res.json()["name"] == "Renamed Healthcare Corp"

        # 3. Upload organization logo
        upload_res = client.post(
            f"/organizations/{org_id}/logo",
            files={"file": ("company-logo.png", b"fake-logo-bytes", "image/png")},
        )
        assert upload_res.status_code == 200
        logo_url = upload_res.json()["logo_url"]
        assert logo_url.startswith("/media/organizations/")
        assert logo_url.endswith(".png")

        # Verify static media serving
        media_res = client.get(logo_url)
        assert media_res.status_code == 200
        assert media_res.content == b"fake-logo-bytes"

        # Verify get_organization shows updated logo_url
        get_after_upload = client.get(f"/organizations/{org_id}")
        assert get_after_upload.status_code == 200
        assert get_after_upload.json()["logo_url"] == logo_url
        assert get_after_upload.json()["name"] == "Renamed Healthcare Corp"

        # Verify auth/me includes organization_logo_url
        me_res = client.get("/auth/me")
        assert me_res.status_code == 200
        assert me_res.json()["membership"]["organization_logo_url"] == logo_url
        assert (
            me_res.json()["membership"]["organization_name"]
            == "Renamed Healthcare Corp"
        )

        # 4. Delete organization logo
        delete_res = client.delete(f"/organizations/{org_id}/logo")
        assert delete_res.status_code == 204

        # Verify logo is cleared
        get_after_delete = client.get(f"/organizations/{org_id}")
        assert get_after_delete.status_code == 200
        assert get_after_delete.json()["logo_url"] is None

    @pytest.mark.asyncio
    async def test_non_admin_cannot_edit_organization(self, client, auth_scenario):
        user = await auth_scenario.register_and_login(
            email="member-only@example.com",
            memberships=[("protected-org", OrgRole.MEMBER)],
        )
        org_id = user.membership.organization_id

        patch_res = client.patch(
            f"/organizations/{org_id}",
            json={"name": "Hacked Name"},
        )
        assert patch_res.status_code == 403

        upload_res = client.post(
            f"/organizations/{org_id}/logo",
            files={"file": ("logo.png", b"data", "image/png")},
        )
        assert upload_res.status_code == 403

        delete_res = client.delete(f"/organizations/{org_id}/logo")
        assert delete_res.status_code == 403
