import uuid

from pydantic import BaseModel, Field


class RiskTrendPointResponse(BaseModel):
    period: str
    month_label: str
    average_score: float
    risk_index: float
    total_assessments: int
    scores_by_study: dict[str, float] = Field(default_factory=dict)


class DepartmentAnalyticsSummaryResponse(BaseModel):
    department_id: uuid.UUID
    name: str
    average_score: float
    total_workers: int
    high_risk_count: int


class RegistrationTrendPointResponse(BaseModel):
    period: str
    date_label: str
    new_members: int
    cumulative_members: int
