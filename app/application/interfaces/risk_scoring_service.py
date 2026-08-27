from typing import Any, Protocol

from app.application.dto.risk_scoring import (
    HealthDataDTO,
    ScoreCatalogItemDTO,
    ScoreResultDTO,
)


class RiskScoringService(Protocol):
    """
    Outbound port for evaluating health risk scores.
    This hides whether the engine is internal or an external HTTP microservice.
    """

    async def get_catalog(self) -> list[ScoreCatalogItemDTO]:
        """Fetch catalog of available risk scores and their field requirements."""
        ...

    async def evaluate_single_score(
        self, score_id: str, payload: dict[str, Any]
    ) -> ScoreResultDTO:
        """Evaluate a specific risk score by its ID with canonical health data payload."""
        ...

    async def evaluate_risk(
        self, data: HealthDataDTO, target_scores: list[str] | None = None
    ) -> list[ScoreResultDTO]:
        """
        Evaluate risk scores using the provided health data.
        """
        ...
