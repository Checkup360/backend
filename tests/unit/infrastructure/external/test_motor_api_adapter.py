import httpx
from unittest.mock import AsyncMock, patch

import pytest

from app.application.dto.risk_scoring import HealthDataDTO
from app.infrastructure.external.motor_api_adapter import HttpMotorScoringAdapter


@pytest.mark.asyncio
async def test_get_catalog_success() -> None:
    motor_url = "http://fake-motor:8000"
    client = httpx.AsyncClient()
    adapter = HttpMotorScoringAdapter(motor_api_url=motor_url, client=client)

    mock_response = httpx.Response(
        status_code=200,
        json=[
            {
                "score_id": "findrisc",
                "score_name": "FINDRISC",
                "domain": "Diabetes",
                "required_fields": ["age", "sex"],
                "optional_fields": ["smoker"],
            }
        ],
        request=httpx.Request("GET", f"{motor_url}/risk-scores/catalog"),
    )

    with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        catalog = await adapter.get_catalog()

    assert len(catalog) == 1
    assert catalog[0].score_id == "findrisc"
    assert catalog[0].required_fields == ["age", "sex"]


@pytest.mark.asyncio
async def test_evaluate_single_score_success() -> None:
    motor_url = "http://fake-motor:8000"
    client = httpx.AsyncClient()
    adapter = HttpMotorScoringAdapter(motor_api_url=motor_url, client=client)

    mock_response = httpx.Response(
        status_code=200,
        json={
            "score_id": "findrisc",
            "score_name": "FINDRISC",
            "domain": "Diabetes",
            "status": "CALCULATED",
            "raw_value": 12.0,
            "normalized_value": None,
            "risk_level": "Moderate",
            "explanation": "Moderate risk of type 2 diabetes.",
            "contributing_factors": {"age": 2},
        },
        request=httpx.Request("POST", f"{motor_url}/risk-scores/findrisc"),
    )

    with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        result = await adapter.evaluate_single_score(
            "findrisc", {"age": 45, "sex": "M"}
        )

    assert result.score_id == "findrisc"
    assert result.raw_value == 12.0
    assert result.risk_level == "Moderate"


@pytest.mark.asyncio
async def test_evaluate_risk_success() -> None:
    motor_url = "http://fake-motor:8000"
    client = httpx.AsyncClient()
    adapter = HttpMotorScoringAdapter(motor_api_url=motor_url, client=client)

    health_data = HealthDataDTO(age=45, sex="M")

    mock_response = httpx.Response(
        status_code=200,
        json={
            "score_id": "findrisc",
            "score_name": "FINDRISC",
            "domain": "Diabetes",
            "status": "CALCULATED",
            "raw_value": 12.0,
            "normalized_value": None,
            "risk_level": "Moderate",
            "explanation": "Moderate risk of type 2 diabetes.",
            "contributing_factors": {"age": 2},
        },
        request=httpx.Request("POST", f"{motor_url}/risk-scores/findrisc"),
    )

    with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        results = await adapter.evaluate_risk(health_data, target_scores=["findrisc"])

    assert len(results) == 1
    assert results[0].score_id == "findrisc"
