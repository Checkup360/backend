import pytest

from app.domain.services.health_topics import active_topics, is_topic_active
from app.domain.value_objects.health_topic import HealthTopic


def test_topic_is_active_only_with_positive_weight():
    org_weights = {"diabetes": 10.0, "eoss": 0.0}
    assert is_topic_active("diabetes", org_weights)
    assert not is_topic_active("eoss", org_weights)
    assert not is_topic_active("audit_c", org_weights)


def test_active_topics_keeps_catalog_order():
    topics = [
        HealthTopic(key="audit_c", label="Alcohol Risk Assessment"),
        HealthTopic(key="diabetes", label="Diabetes"),
        HealthTopic(key="eoss", label="Obesity-related Health Impact"),
    ]
    org_weights = {"diabetes": 10.0, "audit_c": 5.0}
    assert [t.key for t in active_topics(topics, org_weights)] == [
        "audit_c",
        "diabetes",
    ]


@pytest.mark.parametrize("key,label", [("", "Label"), ("key", "  ")])
def test_health_topic_rejects_empty_values(key, label):
    with pytest.raises(ValueError):
        HealthTopic(key=key, label=label)
