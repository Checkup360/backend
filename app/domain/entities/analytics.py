from dataclasses import dataclass
import uuid


@dataclass
class OrganizationRiskTrendPoint:
    period: str
    month_label: str
    average_score: float
    risk_index: float
    total_assessments: int


@dataclass
class DepartmentRiskTrendPoint:
    period: str
    month_label: str
    department_id: uuid.UUID | None
    department_name: str | None
    average_score: float
    risk_index: float
    total_assessments: int


@dataclass
class DepartmentAnalyticsSummary:
    department_id: uuid.UUID
    name: str
    average_score: float
    total_workers: int
    high_risk_count: int
