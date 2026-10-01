from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel


class AssessmentSubmissionSummaryResponse(BaseModel):
    id: uuid.UUID
    form_type: str
    form_version: str
    status: str
    submitted_at: datetime


class AssessmentSubmissionListResponse(BaseModel):
    items: list[AssessmentSubmissionSummaryResponse]
    page: int
    limit: int
    total: int
    has_next: bool


class AssessmentSubmissionAnswersResponse(BaseModel):
    age: int | None = None
    sex: str | None = None
    weight: float | None = None
    height: float | None = None
    waist_circumference: float | None = None
    systolic_blood_pressure: float | None = None
    diastolic_blood_pressure: float | None = None
    total_cholesterol: float | None = None
    hdl: float | None = None
    hdl_cholesterol: float | None = None
    triglycerides: float | None = None
    fasting_glucose: float | None = None
    glucose_lowering_medication: bool | None = None
    smoker: bool | None = None
    daily_physical_activity: bool | None = None
    fruits_vegetables: bool | None = None
    hypertension_medication: bool | None = None
    previous_high_glucose: bool | None = None
    family_diabetes: str | None = None
    snoring: bool | None = None
    tired: bool | None = None
    observed_apnea: bool | None = None
    neck_circumference: float | None = None
    little_interest: int | None = None
    feeling_down: int | None = None
    sleep_trouble: int | None = None
    tired_energy: int | None = None
    appetite: int | None = None
    feeling_bad: int | None = None
    concentration: int | None = None
    psychomotor: int | None = None
    self_harm_thoughts: int | None = None
    eoss_physical_health_stage: int | None = None
    eoss_mental_health_stage: int | None = None
    eoss_functional_stage: int | None = None
    audit_c_frequency: int | None = None
    audit_c_quantity: int | None = None
    audit_c_heavy_drinking: int | None = None
    pss10_q1: int | None = None
    pss10_q2: int | None = None
    pss10_q3: int | None = None
    pss10_q4: int | None = None
    pss10_q5: int | None = None
    pss10_q6: int | None = None
    pss10_q7: int | None = None
    pss10_q8: int | None = None
    pss10_q9: int | None = None
    pss10_q10: int | None = None
    nordic_nmq_data: dict[str, Any] | None = None


class AssessmentSubmissionScoreResponse(BaseModel):
    score_id: uuid.UUID
    score_name: str
    risk_level: str | None = None
    raw_value: float | None = None
    health_index: float | None = None
    explanation: str | None = None
    contributing_factors: dict[str, Any]
    attention_flags: dict[str, bool] = {}
    evaluated_at: datetime


class AssessmentSubmissionDetailResponse(BaseModel):
    id: uuid.UUID
    form_type: str
    form_version: str
    status: str
    submitted_at: datetime
    answers: AssessmentSubmissionAnswersResponse
    scores: list[AssessmentSubmissionScoreResponse]
