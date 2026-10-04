import pytest

from app.domain.services.health_index_classification import (
    classify_health_index,
    needs_attention,
)


@pytest.mark.parametrize(
    "health_index,expected_label",
    [
        (100.0, "Low risk"),
        (80.0, "Low risk"),
        (79.9, "Moderate risk"),
        (50.0, "Moderate risk"),
        (49.9, "Needs attention"),
        (0.0, "Needs attention"),
    ],
)
def test_classify_health_index_higher_is_healthier(
    health_index: float, expected_label: str
) -> None:
    assert classify_health_index(health_index) == expected_label


def test_needs_attention_only_below_moderate_band() -> None:
    assert needs_attention(10.0)
    assert needs_attention(49.9)
    assert not needs_attention(50.0)
    assert not needs_attention(95.0)


def test_custom_risk_thresholds_classification() -> None:
    custom_thresholds = {"low": 85.0, "moderate": 65.0}
    assert classify_health_index(86.0, custom_thresholds) == "Low risk"
    assert classify_health_index(84.0, custom_thresholds) == "Moderate risk"
    assert classify_health_index(65.0, custom_thresholds) == "Moderate risk"
    assert classify_health_index(64.9, custom_thresholds) == "Needs attention"
    assert needs_attention(64.9, custom_thresholds)
    assert not needs_attention(65.0, custom_thresholds)
