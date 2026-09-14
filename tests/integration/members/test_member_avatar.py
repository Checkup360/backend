import pytest
from app.domain.value_objects.org_role import OrgRole


class TestMemberAvatarFlow:
    @pytest.mark.asyncio
    async def test_upload_and_delete_avatar_flow(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="avatar-member@example.com",
            memberships=[("avatar-org", OrgRole.MEMBER)],
        )

        onboarding_res = client.post(
            "/members/me/details",
            json={"date_of_birth": "1990-06-15", "phone_number": "+541112345678"},
        )
        assert onboarding_res.status_code == 200

        upload_res = client.post(
            "/members/me/avatar",
            files={"file": ("profile.png", b"fake-png-data", "image/png")},
        )
        assert upload_res.status_code == 200
        avatar_url = upload_res.json()["avatar_url"]
        assert avatar_url.startswith("/media/avatars/")
        assert avatar_url.endswith(".png")

        profile_res = client.get("/members/me/profile")
        assert profile_res.status_code == 200
        assert profile_res.json()["avatar_url"] == avatar_url

        media_res = client.get(avatar_url)
        assert media_res.status_code == 200
        assert media_res.content == b"fake-png-data"

        delete_res = client.delete("/members/me/avatar")
        assert delete_res.status_code == 204

        profile_after_delete = client.get("/members/me/profile")
        assert profile_after_delete.status_code == 200
        assert profile_after_delete.json()["avatar_url"] is None

    @pytest.mark.asyncio
    async def test_upload_avatar_invalid_format_rejected(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="avatar-invalid@example.com",
            memberships=[("avatar-org-2", OrgRole.MEMBER)],
        )
        client.post(
            "/members/me/details",
            json={"date_of_birth": "1990-06-15"},
        )

        res = client.post(
            "/members/me/avatar",
            files={"file": ("test.pdf", b"%PDF-fake", "application/pdf")},
        )
        assert res.status_code == 422
        assert res.json()["detail"] == "invalid_image_format"

    @pytest.mark.asyncio
    async def test_update_profile_rejects_base64_avatar(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="avatar-base64-reject@example.com",
            memberships=[("avatar-org-3", OrgRole.MEMBER)],
        )
        client.post(
            "/members/me/details",
            json={"date_of_birth": "1990-06-15"},
        )

        res = client.patch(
            "/members/me/profile",
            json={
                "first_name": "Test",
                "last_name": "User",
                "date_of_birth": "1990-06-15",
                "avatar_url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
            },
        )
        assert res.status_code == 422
