"""Unit tests for RecalculateMemberScoresUseCase."""

from datetime import date
import uuid
from unittest.mock import AsyncMock

import pytest

from app.application.dto.risk_scoring import ScoreCatalogItemDTO, ScoreResultDTO
from app.application.use_cases.assessments.recalculate_member_scores import (
    RecalculateMemberScoresUseCase,
)
from app.domain.entities.member_health_data import MemberHealthData
from app.domain.entities.member_details import MemberDetails


@pytest.mark.asyncio
async def test_recalculate_skips_when_no_biometrics():
    biometrics_repo = AsyncMock()
    biometrics_repo.get_by_user.return_value = None
    details_repo = AsyncMock()
    risk_score_repo = AsyncMock()
    scoring_service = AsyncMock()

    use_case = RecalculateMemberScoresUseCase(
        biometrics_repo, details_repo, risk_score_repo, scoring_service
    )
    result = await use_case.execute(uuid.uuid4())
    assert result == []


@pytest.mark.asyncio
async def test_recalculate_filters_incomplete_scores():
    user_id = uuid.uuid4()
    health_data = MemberHealthData(
        user_id=user_id,
        biological_sex="M",
        height=1.75,
        weight=80.0,
        # Missing waist_circumference and neck_circumference
    )

    biometrics_repo = AsyncMock()
    biometrics_repo.get_by_user.return_value = health_data

    details_repo = AsyncMock()
    details_repo.get_by_user.return_value = MemberDetails(
        user_id=user_id, date_of_birth=date(1990, 1, 1)
    )

    risk_score_repo = AsyncMock()
    risk_score_repo.get_by_user_id.return_value = []

    scoring_service = AsyncMock()
    scoring_service.get_catalog.return_value = [
        ScoreCatalogItemDTO(
            score_id="findrisc",
            score_name="FINDRISC",
            domain="Diabetes",
            required_fields=["age", "sex", "weight", "height", "waist_circumference"],
        ),
        ScoreCatalogItemDTO(
            score_id="stop_bang",
            score_name="STOP-BANG",
            domain="Sleep Apnea",
            required_fields=["snoring", "neck_circumference"],
        ),
    ]

    use_case = RecalculateMemberScoresUseCase(
        biometrics_repo, details_repo, risk_score_repo, scoring_service
    )

    result = await use_case.execute(user_id)
    assert result == []
    scoring_service.evaluate_single_score.assert_not_called()


@pytest.mark.asyncio
async def test_recalculate_computes_and_saves_complete_scores():
    user_id = uuid.uuid4()
    health_data = MemberHealthData(
        user_id=user_id,
        biological_sex="M",
        height=1.75,
        weight=80.0,
        waist_circumference=90.0,
        daily_physical_activity=True,
        fruits_vegetables=True,
        hypertension_medication=False,
        previous_high_glucose=False,
        family_diabetes="no",
    )

    biometrics_repo = AsyncMock()
    biometrics_repo.get_by_user.return_value = health_data

    details_repo = AsyncMock()
    details_repo.get_by_user.return_value = MemberDetails(
        user_id=user_id, date_of_birth=date(1980, 5, 10)
    )

    risk_score_repo = AsyncMock()
    risk_score_repo.get_by_user_id.return_value = []

    scoring_service = AsyncMock()
    scoring_service.get_catalog.return_value = [
        ScoreCatalogItemDTO(
            score_id="findrisc",
            score_name="FINDRISC",
            domain="Diabetes",
            required_fields=[
                "age",
                "sex",
                "weight",
                "height",
                "waist_circumference",
                "daily_physical_activity",
                "fruits_vegetables",
                "hypertension_medication",
                "previous_high_glucose",
                "family_diabetes",
            ],
        )
    ]

    scoring_service.evaluate_single_score.return_value = ScoreResultDTO(
        score_id="findrisc",
        score_name="FINDRISC",
        domain="Diabetes",
        status="CALCULATED",
        raw_value=4.0,
        risk_level="Low",
        explanation="Low risk of type 2 diabetes",
        contributing_factors={"age": 0, "bmi": 1},
    )

    use_case = RecalculateMemberScoresUseCase(
        biometrics_repo, details_repo, risk_score_repo, scoring_service
    )

    result = await use_case.execute(user_id)
    assert len(result) == 1
    assert result[0].score_name == "FINDRISC"
    assert result[0].raw_value == 4.0
    risk_score_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_recalculate_computes_score2_when_cardiovascular_fields_present():
    user_id = uuid.uuid4()
    health_data = MemberHealthData(
        user_id=user_id,
        biological_sex="M",
        systolic_blood_pressure=120.0,
        total_cholesterol=200.0,
        hdl_cholesterol=50.0,
        smoker=False,
    )

    biometrics_repo = AsyncMock()
    biometrics_repo.get_by_user.return_value = health_data

    details_repo = AsyncMock()
    details_repo.get_by_user.return_value = MemberDetails(
        user_id=user_id, date_of_birth=date(1975, 1, 1)
    )

    risk_score_repo = AsyncMock()
    risk_score_repo.get_by_user_id.return_value = []

    scoring_service = AsyncMock()
    scoring_service.get_catalog.return_value = [
        ScoreCatalogItemDTO(
            score_id="score2",
            score_name="SCORE2",
            domain="Cardiovascular",
            required_fields=[
                "age",
                "sex",
                "smoker",
                "systolic_blood_pressure",
                "total_cholesterol",
                "hdl_cholesterol",
            ],
            optional_fields=["risk_region"],
        )
    ]

    scoring_service.evaluate_single_score.return_value = ScoreResultDTO(
        score_id="score2",
        score_name="SCORE2",
        domain="Cardiovascular",
        status="CALCULATED",
        raw_value=5.5,
        risk_level="Moderate risk",
        explanation="Estimated 10-year risk of cardiovascular event is 5.5%.",
    )

    use_case = RecalculateMemberScoresUseCase(
        biometrics_repo, details_repo, risk_score_repo, scoring_service
    )

    result = await use_case.execute(user_id)
    assert len(result) == 1
    assert result[0].score_name == "SCORE2"
    assert result[0].raw_value == 5.5
    scoring_service.evaluate_single_score.assert_called_once_with(
        "score2",
        {
            "age": date.today().year
            - 1975
            - ((date.today().month, date.today().day) < (1, 1)),
            "sex": "M",
            "smoker": False,
            "systolic_blood_pressure": 120.0,
            "total_cholesterol": 200.0,
            "hdl_cholesterol": 50.0,
        },
    )


@pytest.mark.asyncio
async def test_recalculate_saves_member_overall_score_when_dependencies_provided():
    from unittest.mock import MagicMock
    from app.domain.entities.risk_score import RiskScore
    from datetime import datetime, timezone

    user_id = uuid.uuid4()
    org_id = uuid.uuid4()
    submission_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    biometrics_repo = AsyncMock()
    biometrics_repo.get_by_user.return_value = MemberHealthData(
        user_id=user_id,
        biological_sex="M",
        height=1.75,
        weight=80.0,
        waist_circumference=90.0,
        daily_physical_activity=True,
        fruits_vegetables=True,
        hypertension_medication=False,
        previous_high_glucose=False,
        family_diabetes="no",
        snoring=False,
        neck_circumference=38.0,
        little_interest=0,
        feeling_down=0,
        sleep_trouble=0,
        tired_energy=0,
        appetite=0,
        feeling_bad=0,
        concentration=0,
        psychomotor=0,
        self_harm_thoughts=0,
    )

    details_repo = AsyncMock()
    details_repo.get_by_user.return_value = MemberDetails(
        user_id=user_id, date_of_birth=date(1990, 1, 1)
    )

    existing_scores = [
        RiskScore(
            id=uuid.uuid4(),
            user_id=user_id,
            score_name="FINDRISC",
            risk_level="Low risk",
            raw_value=4.0,
            health_index=85.0,
            explanation=None,
            contributing_factors={},
            attention_flags={},
            evaluated_at=now,
        ),
        RiskScore(
            id=uuid.uuid4(),
            user_id=user_id,
            score_name="STOP-BANG",
            risk_level="Low risk",
            raw_value=1.0,
            health_index=87.5,
            explanation=None,
            contributing_factors={},
            attention_flags={},
            evaluated_at=now,
        ),
        RiskScore(
            id=uuid.uuid4(),
            user_id=user_id,
            score_name="PHQ-9",
            risk_level="Low risk",
            raw_value=0.0,
            health_index=100.0,
            explanation=None,
            contributing_factors={},
            attention_flags={},
            evaluated_at=now,
        ),
    ]

    risk_score_repo = AsyncMock()
    risk_score_repo.get_by_user_id.return_value = existing_scores

    scoring_service = AsyncMock()
    scoring_service.get_catalog.return_value = []

    overall_score_repo = AsyncMock()
    membership_repo = AsyncMock()
    membership_repo.get_by_user.return_value = MagicMock(organization_id=org_id)

    weights_id = uuid.uuid4()
    weights_repo = AsyncMock()
    weights_repo.get_active_for_organization.return_value = MagicMock(
        id=weights_id,
        organization_id=org_id,
        version=1,
        weights={"diabetes": 34.0, "sleep_apnea": 33.0, "depression": 33.0},
    )

    use_case = RecalculateMemberScoresUseCase(
        member_health_data_repo=biometrics_repo,
        member_details_repo=details_repo,
        risk_score_repo=risk_score_repo,
        risk_scoring_service=scoring_service,
        member_overall_score_repo=overall_score_repo,
        membership_repo=membership_repo,
        score_weights_repo=weights_repo,
    )

    await use_case.execute(user_id=user_id, submission_id=submission_id)

    overall_score_repo.save.assert_awaited_once()
    saved_overall = overall_score_repo.save.call_args[0][0]
    assert saved_overall.user_id == user_id
    assert saved_overall.organization_id == org_id
    assert saved_overall.submission_id == submission_id
    assert saved_overall.score_weights_id == weights_id
    assert (
        saved_overall.overall_health_index == 90.8
    )  # round((85*34 + 87.5*33 + 100*33)/100, 1) = 90.8
    assert saved_overall.risk_level == "Low risk"
