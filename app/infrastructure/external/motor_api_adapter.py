"""HTTP adapter for communicating with the external Motor API."""

from collections.abc import Mapping
from typing import Any

import httpx

from app.application.dto.risk_scoring import HealthDataDTO, ScoreResultDTO
from app.application.interfaces.risk_scoring_service import RiskScoringService


class HttpMotorScoringAdapter(RiskScoringService):
    """
    Infrastructure adapter that implements RiskScoringService by making HTTP calls
    to the external Motor microservice.
    """

    def __init__(self, motor_api_url: str, client: httpx.AsyncClient) -> None:
        self._motor_api_url = motor_api_url.rstrip("/")
        self._client = client

    async def evaluate_risk(
        self, data: HealthDataDTO, target_scores: list[str] | None = None
    ) -> list[ScoreResultDTO]:
        # Build the URL and query parameters
        url = f"{self._motor_api_url}/risk-scores"
        params: list[tuple[str, str]] = []
        if target_scores:
            for score in target_scores:
                params.append(("target_scores", score))

        # Build JSON payload, dropping None values for cleaner payload
        # (Motor API accepts optional fields)
        payload = {k: v for k, v in data.__dict__.items() if v is not None}

        try:
            response = await self._client.post(url, params=params, json=payload)
            response.raise_for_status()
        except httpx.HTTPError as e:
            # Here we might map to a custom domain exception in a real scenario
            raise RuntimeError(f"Failed to communicate with Motor API: {e}") from e

        response_data = response.json()

        # We expect a dict with a "scores" key containing the list of results
        scores_data: list[Mapping[str, Any]] = response_data.get("scores", [])

        results: list[ScoreResultDTO] = []
        for s in scores_data:
            results.append(
                ScoreResultDTO(
                    score_id=s["score_id"],
                    score_name=s["score_name"],
                    domain=s["domain"],
                    status=s["status"],
                    raw_value=s.get("raw_value"),
                    normalized_value=s.get("normalized_value"),
                    risk_level=s.get("risk_level"),
                    explanation=s.get("explanation"),
                    contributing_factors=s.get("contributing_factors", {}),
                )
            )

        return results
