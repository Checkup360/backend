import uuid
from datetime import datetime, date, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.application.use_cases.assessments.submit_assessment import (
    SubmitAssessmentUseCase,
)
from app.application.dto.risk_scoring import HealthDataDTO, ScoreResultDTO
from app.domain.entities.member_details import MemberDetails
from app.domain.entities.risk_score import RiskScore
from app.domain.entities.assessment_submission import AssessmentSubmission


@pytest.mark.asyncio
async def test_submit_assessment_use_case_saves_scores_with_same_timestamp():
    user_id = uuid.uuid4()
    mock_risk_scoring_service = AsyncMock()
    mock_member_details_repo = AsyncMock()
    mock_risk_score_repo = AsyncMock()
    mock_time_provider = MagicMock()

    fixed_now = datetime(2026, 8, 25, 20, 0, 0, tzinfo=timezone.utc)
    mock_time_provider.utcnow.return_value = fixed_now
    mock_time_provider.today.return_value = date(2026, 8, 25)

    mock_member_details = MemberDetails(
        user_id=user_id,
        date_of_birth=date(1990, 5, 15),
    )
    mock_member_details_repo.get_by_user.return_value = mock_member_details

    mock_risk_scoring_service.evaluate_risk.return_value = [
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

    use_case = SubmitAssessmentUseCase(
        risk_scoring_service=mock_risk_scoring_service,
        member_details_repository=mock_member_details_repo,
        risk_score_repository=mock_risk_score_repo,
        time_provider=mock_time_provider,
    )

    input_data = HealthDataDTO(
        sex="male",
        height=180,
        weight=80,
        neck_circumference=41,
        snoring=True,
    )

    results = await use_case.execute(user_id=user_id, health_data=input_data)

    assert len(results) == 2
    assert mock_risk_score_repo.save.call_count == 2

    saved_scores = [call.args[0] for call in mock_risk_score_repo.save.call_args_list]
    assert all(isinstance(s, RiskScore) for s in saved_scores)
    assert saved_scores[0].evaluated_at == fixed_now
    assert saved_scores[1].evaluated_at == fixed_now
    assert saved_scores[0].evaluated_at == saved_scores[1].evaluated_at


@pytest.mark.asyncio
async def test_submit_assessment_use_case_persists_submission_and_links_scores():
    user_id = uuid.uuid4()
    organization_id = uuid.uuid4()
    mock_risk_scoring_service = AsyncMock()
    mock_member_details_repo = AsyncMock()
    mock_risk_score_repo = AsyncMock()
    mock_submission_repo = AsyncMock()
    mock_time_provider = MagicMock()
    fixed_now = datetime(2026, 8, 25, 20, 0, 0, tzinfo=timezone.utc)
    mock_time_provider.utcnow.return_value = fixed_now
    mock_time_provider.today.return_value = date(2026, 8, 25)
    mock_member_details_repo.get_by_user.return_value = MemberDetails(
        user_id=user_id, date_of_birth=date(1990, 5, 15)
    )
    mock_risk_scoring_service.evaluate_risk.return_value = [
        ScoreResultDTO(
            score_id="sb-1",
            score_name="Sleep Apnea",
            domain="clinical",
            status="completed",
        )
    ]
    submission_id = uuid.uuid4()
    mock_submission_repo.save.side_effect = lambda submission: submission.__class__(
        **{**vars(submission), "id": submission_id}
    )

    use_case = SubmitAssessmentUseCase(
        risk_scoring_service=mock_risk_scoring_service,
        member_details_repository=mock_member_details_repo,
        risk_score_repository=mock_risk_score_repo,
        time_provider=mock_time_provider,
        assessment_submission_repository=mock_submission_repo,
    )

    await use_case.execute(
        user_id=user_id,
        organization_id=organization_id,
        health_data=HealthDataDTO(sex="male", weight=80),
    )

    saved_submission = mock_submission_repo.save.call_args.args[0]
    assert isinstance(saved_submission, AssessmentSubmission)
    assert saved_submission.user_id == user_id
    assert saved_submission.organization_id == organization_id
    assert saved_submission.status == "pending"
    saved_score = mock_risk_score_repo.save.call_args.args[0]
    assert saved_score.submission_id == submission_id
    mock_submission_repo.update_status.assert_awaited_once_with(
        submission_id, "completed"
    )
