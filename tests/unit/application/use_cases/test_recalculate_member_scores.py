"""Unit tests for RecalculateMemberScoresUseCase."""

from datetime import date
import uuid
from unittest.mock import AsyncMock

import pytest

from app.application.dto.risk_scoring import ScoreCatalogItemDTO, ScoreResultDTO
from app.application.use_cases.assessments.recalculate_member_scores import (
    RecalculateMemberScoresUseCase,
)
from app.domain.entities.member_biometrics import MemberBiometrics
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
    biometrics = MemberBiometrics(
        user_id=user_id,
        biological_sex="M",
        height=1.75,
        weight=80.0,
        # Missing waist_circumference and neck_circumference
    )

    biometrics_repo = AsyncMock()
    biometrics_repo.get_by_user.return_value = biometrics

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
    biometrics = MemberBiometrics(
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
    biometrics_repo.get_by_user.return_value = biometrics

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
