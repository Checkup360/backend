"""Rules to select which evaluated scores are relevant for an organization."""

from collections.abc import Sequence
from typing import Any, TypeVar

from app.domain.services.health_topics import is_topic_active
from app.domain.services.risk_score_calculator import (
    DEFAULT_SCORE_WEIGHTS,
    normalize_score_key,
)

ScoreT = TypeVar("ScoreT")

LOWEST_HEALTH_INDEX_SCORE_LIMIT = 3


def filter_active_scores(
    scores: Sequence[ScoreT], org_weights: dict[str, float] | None
) -> list[ScoreT]:
    """Scores whose topic is enabled by the organization (weight > 0)."""
    weights = org_weights if org_weights else DEFAULT_SCORE_WEIGHTS
    return [
        score
        for score in scores
        if is_topic_active(normalize_score_key(_score_name(score)), weights)
    ]


def select_lowest_health_index_scores(
    scores: Sequence[ScoreT],
    org_weights: dict[str, float] | None,
    limit: int = LOWEST_HEALTH_INDEX_SCORE_LIMIT,
) -> list[ScoreT]:
    """
    The active, evaluated scores with the lowest health index (the highest
    risk), worst first. Scores that were never evaluated are ignored.
    """
    evaluated_active = [
        score
        for score in filter_active_scores(scores, org_weights)
        if _health_index(score) is not None
    ]
    return sorted(evaluated_active, key=_health_index)[:limit]


def _score_name(score: Any) -> str:
    return getattr(score, "score_name", "") or ""


def _health_index(score: Any) -> float | None:
    return getattr(score, "health_index", None)
