import pytest
from unittest.mock import AsyncMock, patch
import httpx

from app.application.dto.risk_scoring import HealthDataDTO
from app.infrastructure.external.motor_api_adapter import HttpMotorScoringAdapter


@pytest.mark.asyncio
async def test_evaluate_risk_success() -> None:
    # Arrange
    motor_url = "http://fake-motor:8000"
    client = httpx.AsyncClient()
    adapter = HttpMotorScoringAdapter(motor_api_url=motor_url, client=client)

    health_data = HealthDataDTO(
        age=45,
        sex="M",
        weight=90.0,
        height=1.75,
        # other fields are None by default
    )

    mock_response = httpx.Response(
        status_code=200,
        json={
            "scores": [
                {
                    "score_id": "findrisc",
                    "score_name": "FINDRISC",
                    "domain": "Diabetes",
                    "status": "CALCULATED",
                    "raw_value": 12.0,
                    "normalized_value": None,
                    "risk_level": "Moderate",
                    "explanation": "Moderate risk of type 2 diabetes.",
                    "contributing_factors": {"age": 2, "bmi": 3},
                }
            ]
        },
        request=httpx.Request("POST", f"{motor_url}/risk-scores"),
    )

    with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        # Act
        results = await adapter.evaluate_risk(health_data, target_scores=["findrisc"])

    # Assert
    # Check that HTTP client was called correctly
    mock_post.assert_called_once()
    call_args, call_kwargs = mock_post.call_args
    assert call_args[0] == f"{motor_url}/risk-scores"
    assert call_kwargs["params"] == [("target_scores", "findrisc")]

    # Check that None values were dropped from payload
    payload = call_kwargs["json"]
    assert "age" in payload
    assert payload["age"] == 45
    assert "snoring" not in payload

    # Check the returned DTOs
    assert len(results) == 1
    assert results[0].score_id == "findrisc"
    assert results[0].raw_value == 12.0
    assert results[0].risk_level == "Moderate"
    assert results[0].contributing_factors == {"age": 2, "bmi": 3}


@pytest.mark.asyncio
async def test_evaluate_risk_http_error() -> None:
    # Arrange
    motor_url = "http://fake-motor:8000"
    client = httpx.AsyncClient()
    adapter = HttpMotorScoringAdapter(motor_api_url=motor_url, client=client)

    health_data = HealthDataDTO(age=45)

    mock_response = httpx.Response(
        status_code=500,
        text="Internal Server Error",
        request=httpx.Request("POST", f"{motor_url}/risk-scores"),
    )

    with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        # Act & Assert
        with pytest.raises(RuntimeError, match="Failed to communicate with Motor API"):
            await adapter.evaluate_risk(health_data)
