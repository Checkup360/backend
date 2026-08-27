"""HTTP adapter for communicating with the external Engine API."""

from collections.abc import Mapping
from typing import Any

import httpx

from app.application.dto.risk_scoring import (
    HealthDataDTO,
    ScoreCatalogItemDTO,
    ScoreResultDTO,
)
from app.application.interfaces.risk_scoring_service import RiskScoringService


class HttpEngineScoringAdapter(RiskScoringService):
    """
    Infrastructure adapter that implements RiskScoringService by making HTTP calls
    to the external Engine microservice.
    """

    def __init__(self, engine_api_url: str, client: httpx.AsyncClient) -> None:
        self._engine_api_url = engine_api_url.rstrip("/")
        self._client = client

    async def get_catalog(self) -> list[ScoreCatalogItemDTO]:
        """Fetches catalog of available score calculators from the engine."""
        url = f"{self._engine_api_url}/risk-scores/catalog"
        try:
            response = await self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise RuntimeError(
                f"Failed to fetch score catalog from Engine API: {e}"
            ) from e

        catalog_data: list[Mapping[str, Any]] = response.json()
        return [
            ScoreCatalogItemDTO(
                score_id=item["score_id"],
                score_name=item["score_name"],
                domain=item["domain"],
                required_fields=item.get("required_fields", []),
                optional_fields=item.get("optional_fields", []),
            )
            for item in catalog_data
        ]

    async def evaluate_single_score(
        self, score_id: str, payload: dict[str, Any]
    ) -> ScoreResultDTO:
        """Evaluates a single risk score by sending POST to /risk-scores/{score_id}."""
        url = f"{self._engine_api_url}/risk-scores/{score_id}"
        try:
            response = await self._client.post(url, json=payload)
            if response.status_code != 200:
                print(f"ENGINE ERROR for {score_id}: {response.text}", flush=True)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise RuntimeError(
                f"Failed to compute risk score '{score_id}' with Engine API: {e}"
            ) from e

        s = response.json()
        return ScoreResultDTO(
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

    async def evaluate_risk(
        self, data: HealthDataDTO, target_scores: list[str] | None = None
    ) -> list[ScoreResultDTO]:
        """Evaluates multiple risk scores sequentially or based on target_scores."""
        scores_to_evaluate = target_scores
        if not scores_to_evaluate:
            catalog = await self.get_catalog()
            scores_to_evaluate = [item.score_id for item in catalog]

        payload = {k: v for k, v in data.__dict__.items() if v is not None}

        # Translate payload for engine API
        if "sex" in payload and isinstance(payload["sex"], str):
            sex_lower = payload["sex"].lower()
            if sex_lower == "male":
                payload["sex"] = "M"
            elif sex_lower == "female":
                payload["sex"] = "F"

        if "height" in payload and isinstance(payload["height"], (int, float)):
            # Convert cm to meters if height looks like cm
            if payload["height"] > 3.0:
                payload["height"] = payload["height"] / 100.0

        results: list[ScoreResultDTO] = []
        for score_id in scores_to_evaluate:
            try:
                res = await self.evaluate_single_score(score_id, payload)
                results.append(res)
            except Exception as e:
                import logging

                logging.error(f"Failed to evaluate {score_id}: {e}")
                continue

        return results
