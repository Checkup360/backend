import uuid

from app.domain.entities import (
    DepartmentAnalyticsSummary,
    DepartmentRiskTrendPoint,
    OrganizationRiskTrendPoint,
)


def test_organization_risk_trend_point():
    point = OrganizationRiskTrendPoint(
        period="2026-01",
        month_label="Jan",
        average_score=78.5,
        total_assessments=12,
    )
    assert point.period == "2026-01"
    assert point.month_label == "Jan"
    assert point.average_score == 78.5
    assert point.total_assessments == 12


def test_department_risk_trend_point():
    dept_id = uuid.uuid4()
    point = DepartmentRiskTrendPoint(
        period="2026-02",
        month_label="Feb",
        department_id=dept_id,
        department_name="Engineering",
        average_score=85.0,
        total_assessments=8,
    )
    assert point.period == "2026-02"
    assert point.month_label == "Feb"
    assert point.department_id == dept_id
    assert point.department_name == "Engineering"
    assert point.average_score == 85.0
    assert point.total_assessments == 8


def test_department_analytics_summary():
    dept_id = uuid.uuid4()
    summary = DepartmentAnalyticsSummary(
        department_id=dept_id,
        name="Sales",
        average_score=72.4,
        total_workers=30,
        high_risk_count=3,
    )
    assert summary.department_id == dept_id
    assert summary.name == "Sales"
    assert summary.average_score == 72.4
    assert summary.total_workers == 30
    assert summary.high_risk_count == 3
