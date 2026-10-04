from typing import Any

from app.domain.services.health_index_classification import classify_health_index

DEFAULT_SCORE_WEIGHTS: dict[str, float] = {
    "diabetes": 34.0,
    "sleep_apnea": 33.0,
    "depression": 33.0,
}


def normalize_score_key(score_name: str) -> str:
    lower = score_name.lower()
    if "findrisc" in lower or "diabetes" in lower:
        return "diabetes"
    if "stop" in lower or "sleep" in lower:
        return "sleep_apnea"
    if (
        "phq" in lower
        or "depression" in lower
        or "mood" in lower
        or "emotional" in lower
    ):
        return "depression"
    if "metabolic" in lower:
        return "metabolic_syndrome"
    if "eoss" in lower or "obesity" in lower:
        return "eoss"
    if "score2" in lower or "cardiovascular" in lower or "cardio" in lower:
        return "cardiovascular"
    if (
        "nordic" in lower
        or "nmq" in lower
        or "ergonomics" in lower
        or "musculoskeletal" in lower
    ):
        return "nordic_nmq"
    if "audit" in lower or "alcohol" in lower:
        return "audit_c"
    if "pss" in lower or "stress" in lower:
        return "pss10"
    return lower.replace(" ", "_").replace("-", "_")


def calculate_weighted_overall_score(
    results: list[Any],
    weights: dict[str, float] | None = None,
    risk_thresholds: dict[str, float] | None = None,
) -> tuple[float | None, str | None]:
    if not results:
        return None, None

    latest_by_key: dict[str, Any] = {}
    for r in results:
        s_name = getattr(r, "score_name", "") or ""
        key = normalize_score_key(s_name)
        if key not in latest_by_key:
            latest_by_key[key] = r
        else:
            existing_time = getattr(latest_by_key[key], "evaluated_at", None)
            current_time = getattr(r, "evaluated_at", None)
            if current_time and existing_time and current_time > existing_time:
                latest_by_key[key] = r

    score_entries: list[tuple[float, float]] = []
    active_weights = weights if weights and len(weights) > 0 else DEFAULT_SCORE_WEIGHTS

    for key, w in active_weights.items():
        if w > 0 and key in latest_by_key:
            r = latest_by_key[key]
            norm_val = getattr(r, "health_index", None)
            if norm_val is not None:
                score_entries.append((float(norm_val), float(w)))

    # Fallback to any other evaluated score if no active weights matched
    if not score_entries:
        for r in latest_by_key.values():
            norm_val = getattr(r, "health_index", None)
            if norm_val is not None:
                score_entries.append((float(norm_val), 1.0))

    if not score_entries:
        return None, None

    total_weighted_sum = sum(val * w for val, w in score_entries)
    total_weight = sum(w for _, w in score_entries)

    if total_weight <= 0:
        overall_health_index = round(
            sum(val for val, _ in score_entries) / len(score_entries), 1
        )
    else:
        overall_health_index = round(total_weighted_sum / total_weight, 1)

    return overall_health_index, classify_health_index(
        overall_health_index, risk_thresholds
    )
