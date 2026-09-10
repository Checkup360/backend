from typing import Any

DEFAULT_SCORE_WEIGHTS: dict[str, float] = {
    "diabetes": 50.0,
    "sleep_apnea": 50.0,
}


def normalize_score_key(score_name: str) -> str:
    lower = score_name.lower()
    if "findrisc" in lower or "diabetes" in lower:
        return "diabetes"
    if "stop" in lower or "sleep" in lower:
        return "sleep_apnea"
    return lower.replace(" ", "_").replace("-", "_")


def calculate_weighted_overall_score(
    results: list[Any],
    weights: dict[str, float] | None = None,
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

    # All diseases configured with weight > 0 are required to compute overall score
    for key, w in active_weights.items():
        if w > 0:
            if key not in latest_by_key:
                return None, None
            r = latest_by_key[key]
            norm_val = getattr(r, "normalized_value", None)
            if norm_val is None:
                return None, None
            score_entries.append((float(norm_val), float(w)))

    if not score_entries:
        return None, None

    total_weighted_sum = sum(val * w for val, w in score_entries)
    total_weight = sum(w for _, w in score_entries)

    if total_weight <= 0:
        overall_score = round(
            sum(val for val, _ in score_entries) / len(score_entries), 1
        )
    else:
        overall_score = round(total_weighted_sum / total_weight, 1)

    if overall_score >= 85:
        risk_level = "Low risk"
    elif overall_score >= 60:
        risk_level = "Moderate risk"
    else:
        risk_level = "Needs attention"

    return overall_score, risk_level
