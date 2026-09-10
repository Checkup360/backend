from dataclasses import dataclass, field
import uuid


@dataclass
class OrganizationRiskTrendPoint:
    period: str
    month_label: str
    average_score: float
    risk_index: float
    total_assessments: int
    scores_by_study: dict[str, float] = field(default_factory=dict)


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


@dataclass
class OrganizationRegistrationTrendPoint:
    period: str
    date_label: str
    new_members: int
    cumulative_members: int
