import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest


from app.application.dto.risk_scoring import ScoreCatalogItemDTO
from app.application.use_cases.members.get_member_risk_priorities import (
    GetMemberRiskPrioritiesUseCase,
)
from app.domain.exceptions import HealthTopicsUnavailableError
from app.domain.entities.organization import Organization
from app.domain.entities.risk_score import RiskScore


def _catalog_service():
    service = AsyncMock()
    service.get_catalog.return_value = [
        ScoreCatalogItemDTO(
            score_id=score_id,
            score_name=score_id.upper(),
            domain=label,
            topic_key=key,
            topic_label=label,
        )
        for score_id, key, label in [
            ("findrisc", "diabetes", "Diabetes"),
            ("stop_bang", "sleep_apnea", "Sleep Apnea"),
            ("phq9", "depression", "Mood & Well-being"),
            ("audit_c", "audit_c", "Alcohol Risk Assessment"),
        ]
    ]
    return service


@pytest.mark.asyncio
async def test_get_member_risk_priorities_use_case():
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    mock_risk_repo = AsyncMock()
    mock_risk_repo.get_by_user_id.return_value = [
        RiskScore(
            id=uuid.uuid4(),
            user_id=user_id,
            score_name="FINDRISC",
            risk_level="High",
            raw_value=18.0,
            health_index=30.0,
            explanation="High diabetes risk",
            contributing_factors={},
            attention_flags={},
            evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    ]

    mock_org_repo = AsyncMock()
    mock_org_repo.get.return_value = Organization(
        id=org_id,
        name="Acme Corp",
        slug="acme",
        score_weights={"diabetes": 40.0, "sleep_apnea": 30.0, "depression": 30.0},
    )

    use_case = GetMemberRiskPrioritiesUseCase(
        risk_score_repo=mock_risk_repo,
        organization_repo=mock_org_repo,
        risk_scoring_service=_catalog_service(),
    )

    result = await use_case.execute(user_id=user_id, organization_id=org_id)

    assert result.user_id == user_id
    assert result.highest_risk == "diabetes"
    assert "diabetes" in result.risk_weights
    assert result.risk_weights["diabetes"] > result.risk_weights["sleep_apnea"]


@pytest.mark.asyncio
async def test_get_member_risk_priorities_without_active_risks():
    org_id = uuid.uuid4()
    mock_risk_repo = AsyncMock()
    mock_risk_repo.get_by_user_id.return_value = []
    mock_org_repo = AsyncMock()
    mock_org_repo.get.return_value = Organization(
        id=org_id,
        name="Acme Corp",
        slug="acme",
        score_weights={"diabetes": 0.0, "sleep_apnea": 0.0, "depression": 0.0},
    )
    use_case = GetMemberRiskPrioritiesUseCase(
        risk_score_repo=mock_risk_repo,
        organization_repo=mock_org_repo,
        risk_scoring_service=_catalog_service(),
    )

    result = await use_case.execute(user_id=uuid.uuid4(), organization_id=org_id)

    assert result.risk_weights == {}
    assert result.highest_risk is None


@pytest.mark.asyncio
async def test_get_member_risk_priorities_returns_active_categories_with_labels():
    org_id = uuid.uuid4()
    mock_risk_repo = AsyncMock()
    mock_risk_repo.get_by_user_id.return_value = []
    mock_org_repo = AsyncMock()
    mock_org_repo.get.return_value = Organization(
        id=org_id,
        name="Acme Corp",
        slug="acme",
        score_weights={"diabetes": 50.0, "audit_c": 50.0, "depression": 0.0},
    )
    use_case = GetMemberRiskPrioritiesUseCase(
        risk_score_repo=mock_risk_repo,
        organization_repo=mock_org_repo,
        risk_scoring_service=_catalog_service(),
    )

    result = await use_case.execute(user_id=uuid.uuid4(), organization_id=org_id)

    assert set(result.risk_weights) == {"diabetes", "audit_c"}
    assert [(c.key, c.label) for c in result.categories] == [
        ("diabetes", "Diabetes"),
        ("audit_c", "Alcohol Risk Assessment"),
    ]


@pytest.mark.asyncio
async def test_get_member_risk_priorities_fails_when_catalog_is_unavailable():
    service = AsyncMock()
    service.get_catalog.side_effect = RuntimeError("engine down")
    use_case = GetMemberRiskPrioritiesUseCase(
        risk_score_repo=AsyncMock(),
        organization_repo=AsyncMock(),
        risk_scoring_service=service,
    )

    with pytest.raises(HealthTopicsUnavailableError):
        await use_case.execute(user_id=uuid.uuid4())
