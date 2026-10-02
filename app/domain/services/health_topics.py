"""Rules about which health topics are enabled for an organization."""

from collections.abc import Sequence

from app.domain.value_objects.health_topic import HealthTopic


def is_topic_active(topic_key: str, org_weights: dict[str, float]) -> bool:
    """
    A topic is active only when the organization gives it a weight greater
    than zero, the same rule used to decide which health forms are shown.
    """
    return org_weights.get(topic_key, 0.0) > 0


def active_topics(
    topics: Sequence[HealthTopic], org_weights: dict[str, float]
) -> list[HealthTopic]:
    """Topics from the catalog enabled by the organization, in catalog order."""
    return [topic for topic in topics if is_topic_active(topic.key, org_weights)]
