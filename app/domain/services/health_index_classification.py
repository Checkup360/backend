"""Classification rules for health index values.

A health index is a 0-100 value where higher means healthier. Every score
persisted by Checkup360 follows this direction.
"""

MINIMUM_HEALTH_INDEX = 0.0
MAXIMUM_HEALTH_INDEX = 100.0
LOW_RISK_MINIMUM_HEALTH_INDEX = 80.0
MODERATE_RISK_MINIMUM_HEALTH_INDEX = 50.0

LOW_RISK_LABEL = "Low risk"
MODERATE_RISK_LABEL = "Moderate risk"
NEEDS_ATTENTION_LABEL = "Needs attention"


DEFAULT_RISK_THRESHOLDS: dict[str, float] = {
    "low": LOW_RISK_MINIMUM_HEALTH_INDEX,
    "moderate": MODERATE_RISK_MINIMUM_HEALTH_INDEX,
}


def classify_health_index(
    health_index: float,
    thresholds: dict[str, float] | None = None,
) -> str:
    """Returns the overall risk label for a health index using optional custom thresholds."""
    low_thresh = LOW_RISK_MINIMUM_HEALTH_INDEX
    mod_thresh = MODERATE_RISK_MINIMUM_HEALTH_INDEX
    if thresholds:
        if "low" in thresholds:
            low_thresh = float(thresholds["low"])
        elif "low_risk" in thresholds:
            low_thresh = float(thresholds["low_risk"])

        if "moderate" in thresholds:
            mod_thresh = float(thresholds["moderate"])
        elif "moderate_risk" in thresholds:
            mod_thresh = float(thresholds["moderate_risk"])

    if health_index >= low_thresh:
        return LOW_RISK_LABEL
    if health_index >= mod_thresh:
        return MODERATE_RISK_LABEL
    return NEEDS_ATTENTION_LABEL


def needs_attention(
    health_index: float,
    thresholds: dict[str, float] | None = None,
) -> bool:
    """Returns True when the health index falls in the needs-attention band."""
    mod_thresh = MODERATE_RISK_MINIMUM_HEALTH_INDEX
    if thresholds:
        if "moderate" in thresholds:
            mod_thresh = float(thresholds["moderate"])
        elif "moderate_risk" in thresholds:
            mod_thresh = float(thresholds["moderate_risk"])
    return health_index < mod_thresh
