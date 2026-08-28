from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest

from app.infrastructure.persistence.repositories.analytics import (
    AnalyticsRepositoryImpl,
)


@pytest.mark.asyncio
async def test_get_organization_trends():
    mock_db = AsyncMock()
    repo = AnalyticsRepositoryImpl(mock_db)
    org_id = uuid.uuid4()

    mock_row1 = SimpleNamespace(
        period="2026-01",
        month_label="Jan",
        avg_score=80.0,
        total_assessments=10,
    )
    mock_row2 = SimpleNamespace(
        period="2026-02",
        month_label="Feb",
        avg_score=85.0,
        total_assessments=15,
    )

    mock_res = MagicMock()
    mock_res.all.return_value = [mock_row1, mock_row2]
    mock_db.execute.return_value = mock_res

    points = await repo.get_organization_trends(org_id, months=12)

    assert len(points) == 2
    assert points[0].period == "2026-01"
    assert points[0].month_label == "Jan"
    assert points[0].average_score == 80.0
    assert points[0].risk_index == 20.0
    assert points[0].total_assessments == 10

    assert points[1].period == "2026-02"
    assert points[1].month_label == "Feb"
    assert points[1].average_score == 85.0
    assert points[1].risk_index == 15.0
    assert points[1].total_assessments == 15


@pytest.mark.asyncio
async def test_get_departments_summary():
    mock_db = AsyncMock()
    repo = AnalyticsRepositoryImpl(mock_db)
    org_id = uuid.uuid4()
    dept_id = uuid.uuid4()

    mock_dept = SimpleNamespace(id=dept_id, name="Engineering", organization_id=org_id)

    # 1st execute: fetch departments
    mock_depts_res = MagicMock()
    mock_depts_res.scalars.return_value.all.return_value = [mock_dept]

    user_id = uuid.uuid4()
    # 2nd execute: fetch members
    mock_members_res = MagicMock()
    mock_members_res.all.return_value = [(user_id,)]

    # 3rd execute: fetch scores
    mock_scores_row = SimpleNamespace(
        user_id=user_id,
        normalized_value=85.0,
        risk_level="Low",
    )
    mock_scores_res = MagicMock()
    mock_scores_res.all.return_value = [mock_scores_row]

    mock_db.execute.side_effect = [
        mock_depts_res,
        mock_members_res,
        mock_scores_res,
    ]

    summaries = await repo.get_departments_summary(org_id)

    assert len(summaries) == 1
    assert summaries[0].department_id == dept_id
    assert summaries[0].name == "Engineering"
    assert summaries[0].average_score == 85.0
    assert summaries[0].total_workers == 1
    assert summaries[0].high_risk_count == 0
