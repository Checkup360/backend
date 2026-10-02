"""Domain service to calculate clinical risk weights for content prioritization."""

from typing import Sequence
from app.domain.entities.risk_score import RiskScore
from app.domain.services.health_topics import is_topic_active
from app.domain.services.health_index_classification import (
    MAXIMUM_HEALTH_INDEX,
    MINIMUM_HEALTH_INDEX,
)
from app.domain.services.risk_score_calculator import (
    DEFAULT_SCORE_WEIGHTS,
    normalize_score_key,
)


DEFAULT_UNASSESSED_SEVERITY = 0.20


def map_health_index_to_severity(health_index: float | None) -> float:
    """
    Maps health_index (0.0 to 100.0, where higher is healthier) to a
    continuous severity factor [0.0, 1.0], where higher is more severe.
    """
    if health_index is not None:
        clamped = max(MINIMUM_HEALTH_INDEX, min(MAXIMUM_HEALTH_INDEX, health_index))
        severity = (MAXIMUM_HEALTH_INDEX - clamped) / MAXIMUM_HEALTH_INDEX
        return round(severity, 4)

    return DEFAULT_UNASSESSED_SEVERITY


def _latest_score_by_category(scores: Sequence[RiskScore]) -> dict[str, RiskScore]:
    latest_by_key: dict[str, RiskScore] = {}
    for score in scores:
        key = normalize_score_key(score.score_name)
        previous = latest_by_key.get(key)
        if previous is None:
            latest_by_key[key] = score
            continue
        if (
            score.evaluated_at
            and previous.evaluated_at
            and score.evaluated_at > previous.evaluated_at
        ):
            latest_by_key[key] = score
    return latest_by_key


def calculate_member_risk_weights(
    scores: Sequence[RiskScore],
    topic_keys: Sequence[str],
    org_weights: dict[str, float] | None = None,
) -> dict[str, float]:
    """
    Calculates normalized clinical priority weights for a member.
    Balances the member's clinical risk severity (from health_index)
    with their organization's disease weights.

    ``topic_keys`` are the health topics in the scoring catalog. Only topics
    enabled by the organization (weight > 0) are returned, so content about
    disabled risks is never prioritized. Returns a dict mapping active topics
    to normalized weights summing to ~1.0, or an empty dict when the
    organization has no active topic.
    """
    active_org_weights = org_weights if org_weights else DEFAULT_SCORE_WEIGHTS
    categories = [key for key in topic_keys if is_topic_active(key, active_org_weights)]
    if not categories:
        return {}

    latest_by_key = _latest_score_by_category(scores)
    raw_priorities: dict[str, float] = {}
    for cat in categories:
        score = latest_by_key.get(cat)
        health_index = score.health_index if score is not None else None
        severity = map_health_index_to_severity(health_index)
        raw_priorities[cat] = severity * active_org_weights[cat]

    total_raw = sum(raw_priorities.values())
    if total_raw <= 0:
        equal_weight = round(1.0 / len(categories), 4)
        return {cat: equal_weight for cat in categories}

    return {cat: round(raw / total_raw, 4) for cat, raw in raw_priorities.items()}
