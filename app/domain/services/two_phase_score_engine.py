"""Domain service executing the two-phase health domain score calculation engine."""

from datetime import datetime, timezone
from typing import Mapping

from app.domain.entities.health_domain import (
    DomainScore,
    GlobalWeightedIndex,
    HealthDomain,
)

# Mapping from individual calculator names to their primary Health Domain
CALCULATOR_TO_DOMAIN_MAP: dict[str, HealthDomain] = {
    "diabetes": HealthDomain.CARDIOMETABOLIC,
    "findrisc": HealthDomain.CARDIOMETABOLIC,
    "metabolic_syndrome": HealthDomain.CARDIOMETABOLIC,
    "cardiovascular": HealthDomain.CARDIOMETABOLIC,
    "score2": HealthDomain.CARDIOMETABOLIC,
    "sleep_apnea": HealthDomain.FATIGUE_SLEEP,
    "stop_bang": HealthDomain.FATIGUE_SLEEP,
    "depression": HealthDomain.MENTAL_HEALTH,
    "phq9": HealthDomain.MENTAL_HEALTH,
    "eoss": HealthDomain.MENTAL_HEALTH,
}


def _get_risk_level(score: float | None) -> str | None:
    if score is None:
        return None
    if score <= 20.0:
        return "Low risk"
    if score <= 50.0:
        return "Moderate risk"
    return "Needs attention"


class TwoPhaseScoreEngine:
    """
    Two-phase calculation engine:
    Phase 1: Calculates normalized score for each HealthDomain independently.
    Phase 2: Applies employer domain weights to compute the Global Weighted Index.
    """

    def calculate_domain_scores(
        self, calculator_scores: Mapping[str, float]
    ) -> dict[HealthDomain, DomainScore]:
        """
        Phase 1: Aggregates individual calculator scores into domain-level scores.
        """
        domain_sub_scores: dict[HealthDomain, dict[str, float]] = {
            domain: {} for domain in HealthDomain
        }

        for calc_key, val in calculator_scores.items():
            norm_key = calc_key.lower().replace("-", "_").strip()
            domain = CALCULATOR_TO_DOMAIN_MAP.get(norm_key)
            if domain:
                domain_sub_scores[domain][calc_key] = float(val)

        results: dict[HealthDomain, DomainScore] = {}
        now = datetime.now(timezone.utc)

        for domain, sub_scores in domain_sub_scores.items():
            if sub_scores:
                avg_score = round(sum(sub_scores.values()) / len(sub_scores), 1)
                risk_level = _get_risk_level(avg_score)
                results[domain] = DomainScore(
                    domain=domain,
                    normalized_score=avg_score,
                    risk_level=risk_level,
                    sub_scores=sub_scores,
                    evaluated_at=now,
                )
            else:
                results[domain] = DomainScore(
                    domain=domain,
                    normalized_score=None,
                    risk_level=None,
                    sub_scores={},
                    evaluated_at=now,
                )

        return results

    def calculate_global_weighted_index(
        self,
        domain_scores: Mapping[HealthDomain, DomainScore],
        domain_weights: Mapping[str, float] | None = None,
    ) -> GlobalWeightedIndex:
        """
        Phase 2: Computes the Global Weighted Index applying employer domain weights.
        """
        now = datetime.now(timezone.utc)
        if not domain_scores:
            return GlobalWeightedIndex(
                overall_score=None, risk_level=None, domain_scores={}, evaluated_at=now
            )

        active_weighted_entries: list[tuple[float, float]] = []

        if domain_weights:
            for key, weight in domain_weights.items():
                if weight <= 0.0:
                    continue

                norm_key = key.lower().replace("-", "_").strip()

                # Try matching domain enum or legacy calculator key
                matched_domain: HealthDomain | None = None
                try:
                    matched_domain = HealthDomain(norm_key)
                except ValueError:
                    matched_domain = CALCULATOR_TO_DOMAIN_MAP.get(norm_key)

                if matched_domain and matched_domain in domain_scores:
                    d_score = domain_scores[matched_domain].normalized_score
                    if d_score is not None:
                        active_weighted_entries.append((d_score, float(weight)))

        # Fallback if no specific weights given or legacy mode: average all non-None domain scores
        if not active_weighted_entries:
            valid_scores = [
                ds.normalized_score
                for ds in domain_scores.values()
                if ds.normalized_score is not None
            ]
            if not valid_scores:
                return GlobalWeightedIndex(
                    overall_score=None,
                    risk_level=None,
                    domain_scores=dict(domain_scores),
                    evaluated_at=now,
                )
            overall_score = round(sum(valid_scores) / len(valid_scores), 1)
        else:
            total_weighted_sum = sum(score * w for score, w in active_weighted_entries)
            total_weight = sum(w for _, w in active_weighted_entries)
            overall_score = round(total_weighted_sum / total_weight, 1)

        risk_level = _get_risk_level(overall_score)
        return GlobalWeightedIndex(
            overall_score=overall_score,
            risk_level=risk_level,
            domain_scores=dict(domain_scores),
            evaluated_at=now,
        )
