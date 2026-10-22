from datetime import datetime, timezone

from app.presentation.api.response_models.assessments import AssessmentResultResponse
from app.presentation.api.routers.assessments import build_assessments_response

ORG_WEIGHTS = {
    "diabetes": 50.0,
    "sleep_apnea": 50.0,
    "audit_c": 0.0,
}


def _result(score_name: str, health_index: float) -> AssessmentResultResponse:
    return AssessmentResultResponse(
        score_id=score_name,
        score_name=score_name,
        risk_level="moderate",
        raw_value=0,
        health_index=health_index,
        explanation="",
        contributing_factors={},
        attention_flags={},
        evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_member_assessments_hide_scores_disabled_by_organization() -> None:
    results = [_result("Diabetes", 65), _result("Alcohol Habits", 75)]

    response = build_assessments_response(
        results, score_weights=ORG_WEIGHTS, active_scores_only=True
    )

    assert [r.score_name for r in response.results] == ["Diabetes"]
    assert [r.score_name for r in response.sessions[0].results] == ["Diabetes"]
