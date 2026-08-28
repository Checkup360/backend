from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from app.application.use_cases.organizations.get_organization_analytics import (
    GetOrganizationAnalyticsUseCase,
)
from app.domain.entities.analytics import (
    DepartmentAnalyticsSummary,
    OrganizationRiskTrendPoint,
)
from app.domain.exceptions import OrganizationNotFoundError


@pytest.mark.asyncio
async def test_get_trends_success():
    analytics_repo = AsyncMock()
    org_repo = AsyncMock()
    org_id = uuid.uuid4()

    org_mock = MagicMock(id=org_id, name="Health Corp")
    org_repo.get.return_value = org_mock

    mock_point = OrganizationRiskTrendPoint(
        period="2026-01",
        month_label="Jan",
        average_score=80.0,
        risk_index=20.0,
        total_assessments=10,
    )
    analytics_repo.get_organization_trends.return_value = [mock_point]

    use_case = GetOrganizationAnalyticsUseCase(analytics_repo, org_repo)
    result = await use_case.get_trends(org_id, months=12)

    assert len(result) == 1
    assert result[0] == mock_point
    org_repo.get.assert_awaited_once_with(org_id)
    analytics_repo.get_organization_trends.assert_awaited_once_with(
        organization_id=org_id,
        months=12,
        department_id=None,
    )


@pytest.mark.asyncio
async def test_get_trends_org_not_found():
    analytics_repo = AsyncMock()
    org_repo = AsyncMock()
    org_id = uuid.uuid4()
    org_repo.get.return_value = None

    use_case = GetOrganizationAnalyticsUseCase(analytics_repo, org_repo)

    with pytest.raises(OrganizationNotFoundError):
        await use_case.get_trends(org_id)


@pytest.mark.asyncio
async def test_get_departments_summary_success():
    analytics_repo = AsyncMock()
    org_repo = AsyncMock()
    org_id = uuid.uuid4()
    dept_id = uuid.uuid4()

    org_mock = MagicMock(id=org_id, name="Health Corp")
    org_repo.get.return_value = org_mock

    mock_summary = DepartmentAnalyticsSummary(
        department_id=dept_id,
        name="Engineering",
        average_score=85.0,
        total_workers=20,
        high_risk_count=2,
    )
    analytics_repo.get_departments_summary.return_value = [mock_summary]

    use_case = GetOrganizationAnalyticsUseCase(analytics_repo, org_repo)
    result = await use_case.get_departments_summary(org_id)

    assert len(result) == 1
    assert result[0] == mock_summary
    org_repo.get.assert_awaited_once_with(org_id)
    analytics_repo.get_departments_summary.assert_awaited_once_with(org_id)


@pytest.mark.asyncio
async def test_get_departments_summary_org_not_found():
    analytics_repo = AsyncMock()
    org_repo = AsyncMock()
    org_id = uuid.uuid4()
    org_repo.get.return_value = None

    use_case = GetOrganizationAnalyticsUseCase(analytics_repo, org_repo)

    with pytest.raises(OrganizationNotFoundError):
        await use_case.get_departments_summary(org_id)
