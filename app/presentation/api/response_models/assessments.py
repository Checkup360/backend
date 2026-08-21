from pydantic import BaseModel
from typing import Any


class AssessmentResultResponse(BaseModel):
    score_id: str
    score_name: str
    risk_level: str | None = None
    raw_value: float | None = None
    normalized_value: float | None = None
    explanation: str | None = None
    contributing_factors: dict[str, Any] = {}


class AssessmentsResponse(BaseModel):
    results: list[AssessmentResultResponse]
