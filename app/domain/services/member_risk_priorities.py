"""Domain service to calculate clinical risk weights for content prioritization."""

from typing import Sequence
from app.domain.entities.risk_score import RiskScore
from app.domain.services.risk_score_calculator import (
    DEFAULT_SCORE_WEIGHTS,
    normalize_score_key,
)

CLINICAL_CATEGORIES: list[str] = [
    "diabetes",
    "sleep_apnea",
    "depression",
    "metabolic_syndrome",
    "eoss",
]

DEFAULT_UNASSESSED_SEVERITY = 0.20


def map_normalized_value_to_severity(normalized_value: float | None) -> float:
    """
    Maps normalized_value (0.0 to 100.0, where 100 is healthy and 0 is highest risk)
    to a continuous severity factor [0.0, 1.0].
    """
    if normalized_value is not None:
        inv = max(0.0, min(100.0, 100.0 - float(normalized_value))) / 100.0
        return round(inv, 4)

    return DEFAULT_UNASSESSED_SEVERITY


def calculate_member_risk_weights(
    scores: Sequence[RiskScore],
    org_weights: dict[str, float] | None = None,
) -> dict[str, float]:
    """
    Calculates normalized clinical priority weights for a member.
    Balances the member's clinical risk severity (from normalized_value)
    with their organization's disease weights.

    Returns a dict mapping clinical disease categories to normalized weights summing to ~1.0.
    """
    # 1. Extract latest score per disease
    latest_by_key: dict[str, RiskScore] = {}
    for s in scores:
        key = normalize_score_key(s.score_name)
        if key not in latest_by_key:
            latest_by_key[key] = s
        else:
            prev = latest_by_key[key]
            if (
                s.evaluated_at
                and prev.evaluated_at
                and s.evaluated_at > prev.evaluated_at
            ):
                latest_by_key[key] = s

    active_org_weights = (
        org_weights if org_weights and len(org_weights) > 0 else DEFAULT_SCORE_WEIGHTS
    )

    # 2. Compute severity and raw priority per clinical category
    raw_priorities: dict[str, float] = {}
    for cat in CLINICAL_CATEGORIES:
        score = latest_by_key.get(cat)
        if score is not None and score.normalized_value is not None:
            severity = map_normalized_value_to_severity(score.normalized_value)
        else:
            severity = DEFAULT_UNASSESSED_SEVERITY

        # Base org weight: default to 10.0 if not explicitly defined
        w_org = active_org_weights.get(cat, 10.0)
        if w_org <= 0:
            w_org = 5.0  # minimal baseline so clinical risk is not completely erased

        raw_priorities[cat] = severity * w_org

    # 3. Normalize to sum to 1.0
    total_raw = sum(raw_priorities.values())
    if total_raw <= 0:
        equal_weight = round(1.0 / len(CLINICAL_CATEGORIES), 4)
        return {cat: equal_weight for cat in CLINICAL_CATEGORIES}

    normalized: dict[str, float] = {}
    for cat, raw in raw_priorities.items():
        normalized[cat] = round(raw / total_raw, 4)

    return normalized
