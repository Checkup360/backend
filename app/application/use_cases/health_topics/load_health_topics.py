from app.application.interfaces.risk_scoring_service import RiskScoringService
from app.domain.exceptions import HealthTopicsUnavailableError
from app.domain.value_objects.health_topic import HealthTopic


async def load_health_topics(
    risk_scoring_service: RiskScoringService,
) -> list[HealthTopic]:
    """
    Health topics declared by the scoring engine catalog, one per key and in
    catalog order. New scores become available topics without code changes.
    """
    try:
        catalog = await risk_scoring_service.get_catalog()
    except RuntimeError as error:
        raise HealthTopicsUnavailableError() from error

    topics: dict[str, HealthTopic] = {}
    for item in catalog:
        topics.setdefault(
            item.topic_key, HealthTopic(key=item.topic_key, label=item.topic_label)
        )
    return list(topics.values())
