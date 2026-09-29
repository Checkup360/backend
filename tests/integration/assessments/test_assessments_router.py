import pytest
from unittest.mock import AsyncMock
from app.presentation.api.dependencies import get_submit_assessment_use_case
from app.application.use_cases.assessments.submit_assessment import (
    SubmitAssessmentUseCase,
)
from app.application.dto.risk_scoring import ScoreResultDTO


class TestAssessmentsRouter:
    @pytest.mark.asyncio
    async def test_non_member_cannot_evaluate_assessments(self, client, auth_scenario):
        await auth_scenario.register_and_login(
            email="non-member@example.com",
            memberships=None,
        )

        res = client.post(
            "/members/me/assessments/evaluate",
            json={
                "age": 45,
                "sex": "male",
                "height": 175,
                "weight": 70,
                "neck_circumference": 40,
                "snoring": True,
                "tired": False,
                "observed_apnea": False,
                "hypertension_medication": False,
            },
        )
        assert res.status_code == 403
        assert res.json()["detail"] == "forbidden"

    @pytest.mark.asyncio
    async def test_member_can_evaluate_assessments(
        self, client, auth_scenario, monkeypatch
    ):
        # We need a user with a member role
        user = await auth_scenario.register_and_login(
            email="member@example.com",
            memberships=[("my-org", "member")],
        )

        consent_res = client.post(
            "/consents",
            json={"consent_type": "HEALTH_DATA_PROCESSING_CONSENT"},
        )
        assert consent_res.status_code == 201

        # Mock the use case so we don't actually hit the external Engine service
        mock_use_case = AsyncMock(spec=SubmitAssessmentUseCase)
        mock_use_case.execute.return_value = [
            ScoreResultDTO(
                score_id="sb-1",
                score_name="Sleep Apnea",
                domain="clinical",
                status="completed",
                risk_level="High",
                explanation="High risk of sleep apnea",
            ),
            ScoreResultDTO(
                score_id="fr-1",
                score_name="Diabetes",
                domain="clinical",
                status="completed",
                risk_level="Low",
                explanation="Low risk of diabetes",
            ),
        ]

        from app.presentation.main import app

        app.dependency_overrides[get_submit_assessment_use_case] = lambda: mock_use_case

        res = client.post(
            "/members/me/assessments/evaluate",
            json={
                "age": 45,
                "sex": "male",
                "height": 175,
                "weight": 70,
                "neck_circumference": 40,
                "snoring": True,
                "tired": False,
                "observed_apnea": False,
                "hypertension_medication": False,
                "daily_physical_activity": True,
                "fruits_vegetables": True,
                "previous_high_glucose": False,
                "family_diabetes": "no",
                "waist_circumference": 90,
            },
        )

        app.dependency_overrides.clear()

        assert res.status_code == 200
        data = res.json()
        assert "results" in data
        assert len(data["results"]) == 2
        assert data["results"][0]["score_name"] == "Sleep Apnea"
        assert data["results"][0]["risk_level"] == "High"
        assert data["results"][1]["score_name"] == "Diabetes"
        assert data["results"][1]["risk_level"] == "Low"

        # Verify the mock was called correctly
        mock_use_case.execute.assert_called_once()
        kwargs = mock_use_case.execute.call_args.kwargs
        assert kwargs["user_id"] == user.id
        assert "stop_bang" in kwargs["target_scores"]
        assert "findrisc" in kwargs["target_scores"]
        assert "phq9" in kwargs["target_scores"]
        assert kwargs["health_data"].age == 45
        assert kwargs["health_data"].sex == "male"
