from unittest.mock import AsyncMock

import pytest

from app.application.dto.risk_scoring import ScoreCatalogItemDTO
from app.presentation.api.dependencies import get_risk_scoring_service
from app.presentation.main import app


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

        client.post(
            "/consents",
            json={"consent_type": "HEALTH_DATA_PROCESSING_CONSENT"},
        )
        client.post(
            "/consents",
            json={"consent_type": "FORM_CONSENT", "form_type": "biometrics"},
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

    @pytest.mark.asyncio
    async def test_get_my_risk_priorities(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="risk-priorities-user@example.com",
            memberships=None,
        )
        scoring_service = AsyncMock()
        scoring_service.get_catalog.return_value = [
            ScoreCatalogItemDTO(
                score_id=score_id,
                score_name=score_id.upper(),
                domain=label,
                topic_key=key,
                topic_label=label,
            )
            for score_id, key, label in [
                ("findrisc", "diabetes", "Diabetes"),
                ("stop_bang", "sleep_apnea", "Sleep Apnea"),
                ("phq9", "depression", "Mood & Well-being"),
                ("audit_c", "audit_c", "Alcohol Risk Assessment"),
            ]
        ]
        app.dependency_overrides[get_risk_scoring_service] = lambda: scoring_service
        try:
            res = client.get("/members/me/risk-priorities")
        finally:
            app.dependency_overrides.pop(get_risk_scoring_service, None)
        assert res.status_code == 200
        data = res.json()
        assert "user_id" in data
        assert "risk_weights" in data
        assert isinstance(data["risk_weights"], dict)
        assert "diabetes" in data["risk_weights"]
        assert "sleep_apnea" in data["risk_weights"]
        assert "depression" in data["risk_weights"]
        # Default organization weights do not enable alcohol
        assert "audit_c" not in data["risk_weights"]

    @pytest.mark.asyncio
    async def test_get_my_risk_priorities_without_engine_catalog(
        self, client, auth_scenario
    ):
        await auth_scenario.register_and_login(
            email="risk-priorities-engine-down@example.com",
            memberships=None,
        )
        scoring_service = AsyncMock()
        scoring_service.get_catalog.side_effect = RuntimeError("engine down")
        app.dependency_overrides[get_risk_scoring_service] = lambda: scoring_service
        try:
            res = client.get("/members/me/risk-priorities")
        finally:
            app.dependency_overrides.pop(get_risk_scoring_service, None)

        assert res.status_code == 503
        assert res.json()["detail"] == "health_topics_unavailable"
