from dataclasses import dataclass

from app.domain.services.active_score_selection import (
    filter_active_scores,
    select_lowest_health_index_scores,
)


@dataclass
class FakeScore:
    score_name: str
    health_index: float | None


ORG_WEIGHTS = {
    "diabetes": 25.0,
    "sleep_apnea": 25.0,
    "depression": 25.0,
    "cardiovascular": 25.0,
    "pss10": 0.0,
}


def test_filter_active_scores_drops_disabled_topics() -> None:
    scores = [FakeScore("Diabetes", 65), FakeScore("Stress & Burnout", 40)]

    result = filter_active_scores(scores, ORG_WEIGHTS)

    assert [score.score_name for score in result] == ["Diabetes"]


def test_filter_active_scores_drops_topics_missing_from_weights() -> None:
    scores = [FakeScore("Alcohol Habits", 80), FakeScore("Sleep Apnea", 50)]

    result = filter_active_scores(scores, ORG_WEIGHTS)

    assert [score.score_name for score in result] == ["Sleep Apnea"]


def test_filter_active_scores_uses_default_weights_without_org_weights() -> None:
    scores = [FakeScore("Diabetes", 65), FakeScore("Cardiovascular", 70)]

    result = filter_active_scores(scores, None)

    assert [score.score_name for score in result] == ["Diabetes"]


def test_lowest_health_index_returns_three_worst_active_scores_in_order() -> None:
    scores = [
        FakeScore("Diabetes", 65),
        FakeScore("Sleep Apnea", 50),
        FakeScore("Mood & Well-being", 52),
        FakeScore("Cardiovascular", 90),
    ]

    result = select_lowest_health_index_scores(scores, ORG_WEIGHTS)

    assert [score.score_name for score in result] == [
        "Sleep Apnea",
        "Mood & Well-being",
        "Diabetes",
    ]


def test_lowest_health_index_ignores_disabled_even_if_lower() -> None:
    scores = [FakeScore("Stress & Burnout", 10), FakeScore("Diabetes", 65)]

    result = select_lowest_health_index_scores(scores, ORG_WEIGHTS)

    assert [score.score_name for score in result] == ["Diabetes"]


def test_lowest_health_index_ignores_unevaluated_scores() -> None:
    scores = [FakeScore("Diabetes", None), FakeScore("Sleep Apnea", 50)]

    result = select_lowest_health_index_scores(scores, ORG_WEIGHTS)

    assert [score.score_name for score in result] == ["Sleep Apnea"]
