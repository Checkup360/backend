from unittest.mock import AsyncMock
import pytest

from app.presentation.api.dependencies import get_risk_scoring_service
from app.presentation.main import app


class TestMemberFormsRouter:
    @pytest.fixture(autouse=True)
    def mock_risk_scoring_service(self):
        mock_service = AsyncMock()
        mock_service.get_catalog.return_value = []
        app.dependency_overrides[get_risk_scoring_service] = lambda: mock_service
        yield mock_service
        app.dependency_overrides.pop(get_risk_scoring_service, None)

    @pytest.mark.asyncio
    async def test_get_unsupported_form_type_returns_400(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="invalid-form@example.com",
            memberships=None,
        )

        res = client.get("/members/me/forms/unknown_type")
        assert res.status_code == 400
        assert "Unsupported form type" in res.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_and_put_forms_flow(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="forms-flow@example.com",
            memberships=None,
        )

        # GET empty biometrics form
        res_get = client.get("/members/me/forms/biometrics")
        assert res_get.status_code == 200
        assert res_get.json()["form_type"] == "biometrics"
        assert res_get.json()["data"] == {}

        # PUT biometrics form
        res_put = client.put(
            "/members/me/forms/biometrics",
            json={
                "biological_sex": "M",
                "height": 1.80,
                "weight": 85.0,
            },
        )
        assert res_put.status_code == 200
        data_put = res_put.json()
        assert data_put["form_type"] == "biometrics"
        assert data_put["status"] == "success"
        assert "biological_sex" in data_put["updated_fields"]
        assert "height" in data_put["updated_fields"]

        # GET biometrics form again to verify preloaded data
        res_get_again = client.get("/members/me/forms/biometrics")
        assert res_get_again.status_code == 200
        assert res_get_again.json()["data"]["biological_sex"] == "M"
        assert res_get_again.json()["data"]["height"] == 1.80

        # PUT habits form
        res_habits = client.put(
            "/members/me/forms/habits",
            json={
                "daily_physical_activity": True,
                "fruits_vegetables": True,
                "hypertension_medication": False,
                "family_diabetes": "no",
            },
        )
        assert res_habits.status_code == 200
        data_habits = res_habits.json()
        assert data_habits["form_type"] == "habits"
        assert "daily_physical_activity" in data_habits["updated_fields"]

    @pytest.mark.asyncio
    async def test_put_biometrics_in_centimeters(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="cm-height@example.com",
            memberships=None,
        )

        res_put = client.put(
            "/members/me/forms/biometrics",
            json={
                "biological_sex": "M",
                "height": 124,
                "weight": 15,
            },
        )
        assert res_put.status_code == 200

        res_get = client.get("/members/me/forms/biometrics")
        assert res_get.status_code == 200
        assert res_get.json()["data"]["height"] == 124
