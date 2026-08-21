import pytest


class TestMembersRouter:
    @pytest.mark.asyncio
    async def test_non_member_cannot_create_member_details(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="non-member-details@example.com",
            memberships=None,
        )

        res = client.post(
            "/members/me/details",
            json={
                "first_name": "Juan",
                "last_name": "Perez",
                "date_of_birth": "1990-01-01",
                "phone_number": "+541112345678",
            },
        )
        assert res.status_code == 403
        assert res.json()["detail"] == "forbidden"

    @pytest.mark.asyncio
    async def test_get_my_profile_not_found(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="no-profile-user@example.com",
            memberships=None,
        )

        res = client.get("/members/me/profile")
        assert res.status_code == 404
        assert res.json()["detail"] == "profile_not_found"

    @pytest.mark.asyncio
    async def test_update_my_profile_not_found(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="no-profile-update@example.com",
            memberships=None,
        )

        res = client.patch(
            "/members/me/profile",
            json={
                "first_name": "NewFirst",
                "last_name": "NewLast",
                "phone_number": "+541112345678",
                "date_of_birth": "1990-01-01",
            },
        )
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_get_my_biometrics_not_found(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="no-biometrics-user@example.com",
            memberships=None,
        )

        res = client.get("/members/me/biometrics")
        assert res.status_code == 404
        assert res.json()["detail"] == "biometrics_not_found"

    @pytest.mark.asyncio
    async def test_update_my_biometrics(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="biometrics-update@example.com",
            memberships=None,
        )

        res = client.patch(
            "/members/me/biometrics",
            json={
                "biological_sex": "female",
                "height": 165.5,
                "weight": 60.0,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["biological_sex"] == "female"
        assert data["height"] == 165.5
        assert data["weight"] == 60.0
