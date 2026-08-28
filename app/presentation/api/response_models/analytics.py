import uuid

from pydantic import BaseModel


class RiskTrendPointResponse(BaseModel):
    period: str
    month_label: str
    average_score: float
    risk_index: float
    total_assessments: int


class DepartmentAnalyticsSummaryResponse(BaseModel):
    department_id: uuid.UUID
    name: str
    average_score: float
    total_workers: int
    high_risk_count: int
