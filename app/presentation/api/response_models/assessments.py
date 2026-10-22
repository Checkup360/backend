from pydantic import BaseModel
from typing import Any
from datetime import datetime


class AssessmentResultResponse(BaseModel):
    score_id: str
    score_name: str
    risk_level: str | None = None
    raw_value: float | None = None
    health_index: float | None = None
    explanation: str | None = None
    contributing_factors: dict[str, Any] = {}
    attention_flags: dict[str, bool] = {}
    evaluated_at: datetime | None = None


class AssessmentSessionResponse(BaseModel):
    id: str
    evaluated_at: datetime
    overall_health_index: float | None = None
    overall_risk_level: str | None = None
    results: list[AssessmentResultResponse]
    lowest_health_index_results: list[AssessmentResultResponse] = []


class AssessmentsResponse(BaseModel):
    overall_health_index: float | None = None
    overall_risk_level: str | None = None
    risk_thresholds: dict[str, float] | None = None
    total_sessions: int = 0
    page: int = 1
    limit: int = 10
    sessions: list[AssessmentSessionResponse] = []
    results: list[AssessmentResultResponse] = []
    lowest_health_index_results: list[AssessmentResultResponse] = []
