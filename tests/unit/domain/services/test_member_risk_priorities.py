import uuid
from datetime import datetime, timezone

from app.domain.entities.risk_score import RiskScore
from app.domain.services.member_risk_priorities import (
    calculate_member_risk_weights,
    map_health_index_to_severity,
)


TOPIC_KEYS = [
    "diabetes",
    "sleep_apnea",
    "depression",
    "metabolic_syndrome",
    "eoss",
    "cardiovascular",
    "nordic_nmq",
    "audit_c",
    "pss10",
]


def _make_score(
    score_name: str,
    health_index: float | None,
    risk_level: str | None = None,
    evaluated_at: datetime | None = None,
) -> RiskScore:
    return RiskScore(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        score_name=score_name,
        risk_level=risk_level,
        raw_value=10.0,
        health_index=health_index,
        explanation="test",
        contributing_factors={},
        attention_flags={},
        evaluated_at=evaluated_at or datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_map_health_index_to_severity():
    # 100.0 (healthiest) -> 0.0 severity
    assert map_health_index_to_severity(100.0) == 0.0
    # 0.0 (least healthy) -> 1.0 severity
    assert map_health_index_to_severity(0.0) == 1.0
    # 80.0 -> 0.2 severity
    assert map_health_index_to_severity(80.0) == 0.2
    # 50.0 -> 0.5 severity
    assert map_health_index_to_severity(50.0) == 0.5
    # None -> 0.2 baseline
    assert map_health_index_to_severity(None) == 0.2


def test_calculate_member_risk_weights_empty_scores():
    weights = calculate_member_risk_weights([], TOPIC_KEYS)
    assert isinstance(weights, dict)
    assert "diabetes" in weights
    assert "sleep_apnea" in weights
    assert "depression" in weights
    # All weights sum to ~1.0
    assert 0.99 <= sum(weights.values()) <= 1.01


def test_calculate_member_risk_weights_prioritizes_high_risk():
    # Diabetes health_index=10.0 (high risk, severity 0.9)
    # Sleep apnea health_index=90.0 (low risk, severity 0.1)
    # Depression health_index=90.0 (low risk, severity 0.1)
    scores = [
        _make_score("FINDRISC", health_index=10.0),
        _make_score("STOP-BANG", health_index=90.0),
        _make_score("PHQ-9", health_index=90.0),
    ]
    weights = calculate_member_risk_weights(scores, TOPIC_KEYS)
    assert weights["diabetes"] > weights["sleep_apnea"]
    assert weights["diabetes"] > weights["depression"]
    assert 0.99 <= sum(weights.values()) <= 1.01


def test_calculate_member_risk_weights_custom_org_weights():
    # Both have high risk (health_index=10.0), but org prioritizes depression:
    scores = [
        _make_score("FINDRISC", health_index=10.0),
        _make_score("PHQ-9", health_index=10.0),
    ]
    org_weights = {
        "diabetes": 10.0,
        "depression": 80.0,
        "sleep_apnea": 10.0,
    }
    weights = calculate_member_risk_weights(scores, TOPIC_KEYS, org_weights)
    assert weights["depression"] > weights["diabetes"]


def test_calculate_member_risk_weights_latest_score_only():
    t_old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    t_new = datetime(2026, 2, 1, tzinfo=timezone.utc)
    improved = calculate_member_risk_weights(
        [
            _make_score("FINDRISC", health_index=10.0, evaluated_at=t_old),
            _make_score("FINDRISC", health_index=90.0, evaluated_at=t_new),
        ],
        TOPIC_KEYS,
    )
    worsened = calculate_member_risk_weights(
        [
            _make_score("FINDRISC", health_index=90.0, evaluated_at=t_old),
            _make_score("FINDRISC", health_index=10.0, evaluated_at=t_new),
        ],
        TOPIC_KEYS,
    )
    # Only the latest score counts: improving lowers the diabetes priority
    assert improved["diabetes"] < worsened["diabetes"]


def test_calculate_member_risk_weights_excludes_disabled_categories():
    org_weights = {"diabetes": 50.0, "sleep_apnea": 0.0, "depression": 50.0}
    weights = calculate_member_risk_weights(
        [_make_score("STOP-BANG", health_index=5.0)], TOPIC_KEYS, org_weights
    )
    # Disabled (0) and missing categories never get a weight, even with high risk
    assert set(weights) == {"diabetes", "depression"}
    assert 0.99 <= sum(weights.values()) <= 1.01


def test_calculate_member_risk_weights_without_active_categories_is_empty():
    org_weights = {"diabetes": 0.0, "sleep_apnea": 0.0}
    assert calculate_member_risk_weights([], TOPIC_KEYS, org_weights) == {}


def test_calculate_member_risk_weights_includes_any_active_catalog_topic():
    # Alcohol is not a "clinical" disease, but it is an active catalog topic
    org_weights = {"diabetes": 50.0, "audit_c": 50.0}
    weights = calculate_member_risk_weights(
        [_make_score("AUDIT-C Alcohol Risk", health_index=10.0)],
        TOPIC_KEYS,
        org_weights,
    )
    assert set(weights) == {"diabetes", "audit_c"}
    assert weights["audit_c"] > weights["diabetes"]


def test_calculate_member_risk_weights_ignores_weights_outside_the_catalog():
    org_weights = {"diabetes": 50.0, "unknown_topic": 50.0}
    weights = calculate_member_risk_weights([], TOPIC_KEYS, org_weights)
    assert set(weights) == {"diabetes"}
