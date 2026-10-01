import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.application.use_cases.members.get_member_risk_priorities import (
    GetMemberRiskPrioritiesUseCase,
)
from app.domain.entities.organization import Organization
from app.domain.entities.risk_score import RiskScore


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
    )

    result = await use_case.execute(user_id=user_id, organization_id=org_id)

    assert result.user_id == user_id
    assert result.highest_risk == "diabetes"
    assert "diabetes" in result.risk_weights
    assert result.risk_weights["diabetes"] > result.risk_weights["sleep_apnea"]
