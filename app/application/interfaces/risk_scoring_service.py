"""Interface for the Risk Scoring Engine port."""

from typing import Protocol

from app.application.dto.risk_scoring import HealthDataDTO, ScoreResultDTO


class RiskScoringService(Protocol):
    """
    Outbound port for evaluating health risk scores.
    This hides whether the engine is internal or an external HTTP microservice.
    """

    async def evaluate_risk(
        self, data: HealthDataDTO, target_scores: list[str] | None = None
    ) -> list[ScoreResultDTO]:
        """
        Evaluate risk scores using the provided health data.

        Args:
            data: The health parameters of the employee.
            target_scores: Optional list of specific score IDs to evaluate (e.g., ["findrisc"]).
                           If None, evaluates all available scores.

        Returns:
            A list of computed score results.
        """
        ...
