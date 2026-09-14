from datetime import datetime, timezone
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
    user_id = uuid.uuid4()
    now_jan = datetime(2026, 1, 15, tzinfo=timezone.utc)
    now_feb = datetime(2026, 2, 15, tzinfo=timezone.utc)

    # 1st execute: org score weights
    mock_org_res = MagicMock()
    mock_org_res.scalar_one_or_none.return_value = None

    # 2nd execute: raw scores to compute user overall score & per-study score
    mock_rows = [
        SimpleNamespace(
            period="2026-01",
            month_label="Jan",
            user_id=user_id,
            score_name="Diabetes",
            normalized_value=80.0,
            evaluated_at=now_jan,
        ),
        SimpleNamespace(
            period="2026-01",
            month_label="Jan",
            user_id=user_id,
            score_name="Sleep Apnea",
            normalized_value=80.0,
            evaluated_at=now_jan,
        ),
        SimpleNamespace(
            period="2026-01",
            month_label="Jan",
            user_id=user_id,
            score_name="Depression",
            normalized_value=80.0,
            evaluated_at=now_jan,
        ),
        SimpleNamespace(
            period="2026-02",
            month_label="Feb",
            user_id=user_id,
            score_name="Diabetes",
            normalized_value=85.0,
            evaluated_at=now_feb,
        ),
        SimpleNamespace(
            period="2026-02",
            month_label="Feb",
            user_id=user_id,
            score_name="Sleep Apnea",
            normalized_value=85.0,
            evaluated_at=now_feb,
        ),
        SimpleNamespace(
            period="2026-02",
            month_label="Feb",
            user_id=user_id,
            score_name="Depression",
            normalized_value=85.0,
            evaluated_at=now_feb,
        ),
    ]
    mock_scores_res = MagicMock()
    mock_scores_res.all.return_value = mock_rows

    mock_db.execute.side_effect = [mock_org_res, mock_scores_res]

    points = await repo.get_organization_trends(org_id, months=12)

    assert len(points) == 2
    assert points[0].period == "2026-01"
    assert points[0].month_label == "Jan"
    assert points[0].average_score == 80.0
    assert points[0].risk_index == 80.0
    assert points[0].total_assessments == 3
    assert points[0].scores_by_study == {
        "Diabetes": 80.0,
        "Sleep Apnea": 80.0,
        "Depression": 80.0,
    }
    assert points[1].scores_by_study == {
        "Diabetes": 85.0,
        "Sleep Apnea": 85.0,
        "Depression": 85.0,
    }

    assert points[1].period == "2026-02"
    assert points[1].month_label == "Feb"
    assert points[1].average_score == 85.0
    assert points[1].risk_index == 85.0
    assert points[1].total_assessments == 3


@pytest.mark.asyncio
async def test_get_departments_summary():
    mock_db = AsyncMock()
    repo = AnalyticsRepositoryImpl(mock_db)
    org_id = uuid.uuid4()
    dept_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    mock_dept = SimpleNamespace(id=dept_id, name="Engineering", organization_id=org_id)

    # 1st execute: fetch departments
    mock_depts_res = MagicMock()
    mock_depts_res.scalars.return_value.all.return_value = [mock_dept]

    # 2nd execute: fetch org score weights
    mock_org_res = MagicMock()
    mock_org_res.scalar_one_or_none.return_value = None

    user_id = uuid.uuid4()
    # 3rd execute: fetch members
    mock_members_res = MagicMock()
    mock_members_res.all.return_value = [(user_id,)]

    # 4th execute: fetch scores (all 3 required forms completed)
    mock_scores_rows = [
        SimpleNamespace(
            user_id=user_id,
            score_name="Diabetes",
            normalized_value=15.0,
            risk_level="Low risk",
            evaluated_at=now,
        ),
        SimpleNamespace(
            user_id=user_id,
            score_name="Sleep Apnea",
            normalized_value=15.0,
            risk_level="Low risk",
            evaluated_at=now,
        ),
        SimpleNamespace(
            user_id=user_id,
            score_name="Depression",
            normalized_value=15.0,
            risk_level="Low risk",
            evaluated_at=now,
        ),
    ]
    mock_scores_res = MagicMock()
    mock_scores_res.all.return_value = mock_scores_rows

    mock_db.execute.side_effect = [
        mock_depts_res,
        mock_org_res,
        mock_members_res,
        mock_scores_res,
    ]

    summaries = await repo.get_departments_summary(org_id)

    assert len(summaries) == 1
    assert summaries[0].department_id == dept_id
    assert summaries[0].name == "Engineering"
    assert summaries[0].average_score == 15.0
    assert summaries[0].total_workers == 1
    assert summaries[0].high_risk_count == 0


@pytest.mark.asyncio
async def test_get_registration_trends():
    mock_db = AsyncMock()
    repo = AnalyticsRepositoryImpl(mock_db)
    org_id = uuid.uuid4()

    mock_row1 = SimpleNamespace(
        period="2026-09-01",
        date_label="01 Sep",
        new_members=3,
    )
    mock_row2 = SimpleNamespace(
        period="2026-09-02",
        date_label="02 Sep",
        new_members=2,
    )

    mock_res = MagicMock()
    mock_res.all.return_value = [mock_row1, mock_row2]
    mock_db.execute.return_value = mock_res

    points = await repo.get_registration_trends(org_id)

    assert len(points) == 2
    assert points[0].period == "2026-09-01"
    assert points[0].date_label == "01 Sep"
    assert points[0].new_members == 3
    assert points[0].cumulative_members == 3

    assert points[1].period == "2026-09-02"
    assert points[1].date_label == "02 Sep"
    assert points[1].new_members == 2
    assert points[1].cumulative_members == 5
