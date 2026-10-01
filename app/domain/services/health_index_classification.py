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


def classify_health_index(health_index: float) -> str:
    """Returns the overall risk label for a health index."""
    if health_index >= LOW_RISK_MINIMUM_HEALTH_INDEX:
        return LOW_RISK_LABEL
    if health_index >= MODERATE_RISK_MINIMUM_HEALTH_INDEX:
        return MODERATE_RISK_LABEL
    return NEEDS_ATTENTION_LABEL


def needs_attention(health_index: float) -> bool:
    """Returns True when the health index falls in the needs-attention band."""
    return health_index < MODERATE_RISK_MINIMUM_HEALTH_INDEX
