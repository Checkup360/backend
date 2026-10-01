from dataclasses import dataclass
from datetime import datetime, timezone
from app.domain.services.risk_score_calculator import (
    calculate_weighted_overall_score,
    normalize_score_key,
)


@dataclass
class DummyScoreResult:
    score_name: str
    health_index: float | None
    evaluated_at: datetime | None = None


def test_normalize_score_key():
    assert normalize_score_key("FINDRISC") == "diabetes"
    assert normalize_score_key("Diabetes") == "diabetes"
    assert normalize_score_key("STOP-BANG") == "sleep_apnea"
    assert normalize_score_key("Sleep Apnea") == "sleep_apnea"
    assert normalize_score_key("PHQ-9") == "depression"
    assert normalize_score_key("Depression") == "depression"
    assert normalize_score_key("Mood and Emotional Well-being") == "depression"
    assert normalize_score_key("Metabolic Syndrome") == "metabolic_syndrome"
    assert normalize_score_key("Metabolic Health") == "metabolic_syndrome"
    assert normalize_score_key("EOSS") == "eoss"
    assert normalize_score_key("Obesity-related Health Impact") == "eoss"
    assert normalize_score_key("SCORE2") == "cardiovascular"
    assert normalize_score_key("Cardiovascular Health") == "cardiovascular"
    assert normalize_score_key("Cardiovascular Risk") == "cardiovascular"
    assert normalize_score_key("Custom-Score") == "custom_score"


def test_calculate_weighted_overall_score_empty():
    score, level = calculate_weighted_overall_score([])
    assert score is None
    assert level is None


def test_calculate_weighted_overall_score_default_weights():
    results = [
        DummyScoreResult(score_name="Diabetes", health_index=90.0),
        DummyScoreResult(score_name="Sleep Apnea", health_index=90.0),
        DummyScoreResult(score_name="Depression", health_index=90.0),
    ]
    score, level = calculate_weighted_overall_score(results)
    assert score == 90.0
    assert level == "Low risk"


def test_calculate_weighted_overall_score_custom_weights():
    # Diabetes: 90, Sleep Apnea: 70 with weights 80% Diabetes / 20% Sleep Apnea
    # (90*80 + 70*20)/100 = (7200 + 1400)/100 = 86.0 -> Low risk
    results = [
        DummyScoreResult(score_name="Diabetes", health_index=90.0),
        DummyScoreResult(score_name="Sleep Apnea", health_index=70.0),
    ]
    weights = {"diabetes": 80.0, "sleep_apnea": 20.0}
    score, level = calculate_weighted_overall_score(results, weights)
    assert score == 86.0
    assert level == "Low risk"


def test_calculate_weighted_overall_score_includes_new_score_weights():
    results = [
        DummyScoreResult(score_name="Diabetes", health_index=100.0),
        DummyScoreResult(score_name="Metabolic Syndrome", health_index=0.0),
    ]
    score, level = calculate_weighted_overall_score(
        results,
        weights={"diabetes": 80.0, "metabolic_syndrome": 20.0},
    )

    assert score == 80.0
    assert level == "Low risk"


def test_calculate_weighted_overall_score_partial_results():
    # Employee only completed Diabetes (health index 70) with custom weights 60/40
    # Because sleep_apnea is missing, overall score cannot be computed
    results = [
        DummyScoreResult(score_name="Diabetes", health_index=70.0),
    ]
    weights = {"diabetes": 60.0, "sleep_apnea": 40.0}
    score, level = calculate_weighted_overall_score(results, weights)
    assert score is None
    assert level is None


def test_calculate_weighted_overall_score_zero_weight_for_missing_score():
    # If a disease has 0 weight, its absence does not block overall score
    results = [
        DummyScoreResult(score_name="Diabetes", health_index=70.0),
    ]
    weights = {"diabetes": 100.0, "sleep_apnea": 0.0}
    score, level = calculate_weighted_overall_score(results, weights)
    assert score == 70.0
    assert level == "Moderate risk"


def test_calculate_weighted_overall_score_latest_timestamp_filtering():
    t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2026, 2, 1, tzinfo=timezone.utc)
    results = [
        DummyScoreResult(score_name="Diabetes", health_index=50.0, evaluated_at=t1),
        DummyScoreResult(score_name="Diabetes", health_index=90.0, evaluated_at=t2),
        DummyScoreResult(score_name="Sleep Apnea", health_index=90.0, evaluated_at=t2),
        DummyScoreResult(score_name="Depression", health_index=90.0, evaluated_at=t2),
    ]
    score, level = calculate_weighted_overall_score(results)
    assert score == 90.0
    assert level == "Low risk"


def test_calculate_weighted_overall_score_low_health_index_needs_attention():
    results = [
        DummyScoreResult(score_name="Diabetes", health_index=20.0),
        DummyScoreResult(score_name="Sleep Apnea", health_index=30.0),
        DummyScoreResult(score_name="Depression", health_index=40.0),
    ]
    score, level = calculate_weighted_overall_score(results)
    assert score is not None
    assert score < 50.0
    assert level == "Needs attention"
