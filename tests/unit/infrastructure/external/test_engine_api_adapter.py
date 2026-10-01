import httpx
from unittest.mock import AsyncMock, patch

import pytest

from app.application.dto.risk_scoring import HealthDataDTO
from app.infrastructure.external.engine_api_adapter import HttpEngineScoringAdapter


@pytest.mark.asyncio
async def test_get_catalog_success() -> None:
    engine_url = "http://fake-engine:8000"
    client = httpx.AsyncClient()
    adapter = HttpEngineScoringAdapter(engine_api_url=engine_url, client=client)

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
        request=httpx.Request("GET", f"{engine_url}/risk-scores/catalog"),
    )

    with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        catalog = await adapter.get_catalog()

    assert len(catalog) == 1
    assert catalog[0].score_id == "findrisc"
    assert catalog[0].required_fields == ["age", "sex"]


@pytest.mark.asyncio
async def test_evaluate_single_score_success() -> None:
    engine_url = "http://fake-engine:8000"
    client = httpx.AsyncClient()
    adapter = HttpEngineScoringAdapter(engine_api_url=engine_url, client=client)

    mock_response = httpx.Response(
        status_code=200,
        json={
            "score_id": "findrisc",
            "score_name": "FINDRISC",
            "domain": "Diabetes",
            "status": "CALCULATED",
            "raw_value": 12.0,
            "health_index": 53.8,
            "risk_level": "Moderate",
            "explanation": "Moderate risk of type 2 diabetes.",
            "contributing_factors": {"age": 2},
        },
        request=httpx.Request("POST", f"{engine_url}/risk-scores/findrisc"),
    )

    with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        result = await adapter.evaluate_single_score(
            "findrisc", {"age": 45, "sex": "M"}
        )

    assert result.score_id == "findrisc"
    assert result.raw_value == 12.0
    assert result.health_index == 53.8
    assert result.risk_level == "Moderate"


@pytest.mark.asyncio
async def test_evaluate_risk_success() -> None:
    engine_url = "http://fake-engine:8000"
    client = httpx.AsyncClient()
    adapter = HttpEngineScoringAdapter(engine_api_url=engine_url, client=client)

    health_data = HealthDataDTO(age=45, sex="M")

    mock_response = httpx.Response(
        status_code=200,
        json={
            "score_id": "findrisc",
            "score_name": "FINDRISC",
            "domain": "Diabetes",
            "status": "CALCULATED",
            "raw_value": 12.0,
            "health_index": None,
            "risk_level": "Moderate",
            "explanation": "Moderate risk of type 2 diabetes.",
            "contributing_factors": {"age": 2},
        },
        request=httpx.Request("POST", f"{engine_url}/risk-scores/findrisc"),
    )

    with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        results = await adapter.evaluate_risk(health_data, target_scores=["findrisc"])

    assert len(results) == 1
    assert results[0].score_id == "findrisc"


@pytest.mark.asyncio
async def test_evaluate_single_score_translates_cm_to_meters_and_sex() -> None:
    engine_url = "http://fake-engine:8000"
    client = httpx.AsyncClient()
    adapter = HttpEngineScoringAdapter(engine_api_url=engine_url, client=client)

    mock_response = httpx.Response(
        status_code=200,
        json={
            "score_id": "findrisc",
            "score_name": "FINDRISC",
            "domain": "Diabetes",
            "status": "CALCULATED",
            "raw_value": 10.0,
            "health_index": None,
            "risk_level": "Low",
            "explanation": "Low risk.",
            "contributing_factors": {},
        },
        request=httpx.Request("POST", f"{engine_url}/risk-scores/findrisc"),
    )

    with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        # Pass height in cm (175) and sex as 'male'
        await adapter.evaluate_single_score(
            "findrisc", {"age": 30, "sex": "male", "height": 175.0, "weight": 70.0}
        )

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        sent_json = call_kwargs["json"]
        assert sent_json["sex"] == "M"
        assert sent_json["height"] == 1.75


@pytest.mark.asyncio
async def test_evaluate_risk_translates_cm_to_meters() -> None:
    engine_url = "http://fake-engine:8000"
    client = httpx.AsyncClient()
    adapter = HttpEngineScoringAdapter(engine_api_url=engine_url, client=client)

    health_data = HealthDataDTO(age=30, sex="female", height=165.0, weight=60.0)

    mock_response = httpx.Response(
        status_code=200,
        json={
            "score_id": "findrisc",
            "score_name": "FINDRISC",
            "domain": "Diabetes",
            "status": "CALCULATED",
            "raw_value": 5.0,
            "health_index": None,
            "risk_level": "Low",
            "explanation": "Low risk.",
            "contributing_factors": {},
        },
        request=httpx.Request("POST", f"{engine_url}/risk-scores/findrisc"),
    )

    with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        await adapter.evaluate_risk(health_data, target_scores=["findrisc"])

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        sent_json = call_kwargs["json"]
        assert sent_json["sex"] == "F"
        assert sent_json["height"] == 1.65


@pytest.mark.asyncio
async def test_evaluate_single_score_handles_error_and_raises() -> None:
    engine_url = "http://fake-engine:8000"
    client = httpx.AsyncClient()
    adapter = HttpEngineScoringAdapter(engine_api_url=engine_url, client=client)

    mock_response = httpx.Response(
        status_code=422,
        text='{"detail": "invalid health value"}',
        request=httpx.Request("POST", f"{engine_url}/risk-scores/findrisc"),
    )

    with patch.object(client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        with pytest.raises(RuntimeError) as exc_info:
            await adapter.evaluate_single_score("findrisc", {"age": 45})

        assert "Failed to compute risk score 'findrisc'" in str(exc_info.value)
