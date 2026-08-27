"""Response models for modular member health forms."""

from typing import Any
from pydantic import BaseModel, Field


class MemberFormResponse(BaseModel):
    """Response containing preloaded data for a specific form type."""

    form_type: str
    data: dict[str, Any] = Field(default_factory=dict)


class EvaluatedScoreSummary(BaseModel):
    """Summary of a calculated risk score during form submission."""

    score_name: str
    risk_level: str | None = None
    raw_value: float | None = None
    explanation: str | None = None


class MemberFormSubmissionResponse(BaseModel):
    """Response returned after submitting/updating a health form."""

    form_type: str
    status: str = "success"
    updated_fields: list[str] = Field(default_factory=list)
    recalculated_scores: list[EvaluatedScoreSummary] = Field(default_factory=list)
