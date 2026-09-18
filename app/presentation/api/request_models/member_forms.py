"""Request models for modular member health forms."""

from typing import Literal
from pydantic import BaseModel, Field


class MemberFormUpdate(BaseModel):
    """Generic payload for form update endpoints."""

    # Biometrics fields
    biological_sex: Literal["M", "F"] | None = Field(default=None)
    height: float | None = Field(default=None, gt=0, lt=300, description="Height in cm")
    weight: float | None = Field(default=None, gt=0, lt=500)
    waist_circumference: float | None = Field(default=None, gt=0, lt=300)
    neck_circumference: float | None = Field(default=None, gt=0, lt=100)

    # Metabolic syndrome & cardiovascular fields
    triglycerides: float | None = Field(default=None, ge=0, lt=10000)
    total_cholesterol: float | None = Field(default=None, ge=0, lt=1000)
    hdl_cholesterol: float | None = Field(default=None, ge=0, lt=1000)
    systolic_blood_pressure: float | None = Field(default=None, gt=0, lt=400)
    diastolic_blood_pressure: float | None = Field(default=None, gt=0, lt=300)
    fasting_glucose: float | None = Field(default=None, ge=0, lt=2000)
    glucose_lowering_medication: bool | None = Field(default=None)
    statins: bool | None = Field(default=None)
    lab_study_date: str | None = Field(
        default=None, description="Date of lab study (YYYY-MM-DD)"
    )

    # EOSS self-assessment stages
    eoss_physical_health_stage: int | None = Field(default=None, ge=0, le=4)
    eoss_mental_health_stage: int | None = Field(default=None, ge=0, le=4)
    eoss_functional_stage: int | None = Field(default=None, ge=0, le=4)

    # Sleep fields
    snoring: bool | None = Field(default=None)
    tired: bool | None = Field(default=None)
    observed_apnea: bool | None = Field(default=None)

    # Habits fields
    daily_physical_activity: bool | None = Field(default=None)
    fruits_vegetables: bool | None = Field(default=None)
    hypertension_medication: bool | None = Field(default=None)
    previous_high_glucose: bool | None = Field(default=None)
    smoker: bool | None = Field(default=None)
    family_diabetes: Literal["no", "second_degree", "first_degree"] | None = Field(
        default=None
    )

    # Mood (PHQ-9) fields: 0 = not at all … 3 = nearly every day
    little_interest: int | None = Field(default=None, ge=0, le=3)
    feeling_down: int | None = Field(default=None, ge=0, le=3)
    sleep_trouble: int | None = Field(default=None, ge=0, le=3)
    tired_energy: int | None = Field(default=None, ge=0, le=3)
    appetite: int | None = Field(default=None, ge=0, le=3)
    feeling_bad: int | None = Field(default=None, ge=0, le=3)
    concentration: int | None = Field(default=None, ge=0, le=3)
    psychomotor: int | None = Field(default=None, ge=0, le=3)
    self_harm_thoughts: int | None = Field(default=None, ge=0, le=3)

    # AUDIT-C alcohol risk fields: 0..4
    audit_c_frequency: int | None = Field(default=None, ge=0, le=4)
    audit_c_quantity: int | None = Field(default=None, ge=0, le=4)
    audit_c_heavy_drinking: int | None = Field(default=None, ge=0, le=4)

    # PSS-10 perceived stress scale fields: 0..4
    pss10_q1: int | None = Field(default=None, ge=0, le=4)
    pss10_q2: int | None = Field(default=None, ge=0, le=4)
    pss10_q3: int | None = Field(default=None, ge=0, le=4)
    pss10_q4: int | None = Field(default=None, ge=0, le=4)
    pss10_q5: int | None = Field(default=None, ge=0, le=4)
    pss10_q6: int | None = Field(default=None, ge=0, le=4)
    pss10_q7: int | None = Field(default=None, ge=0, le=4)
    pss10_q8: int | None = Field(default=None, ge=0, le=4)
    pss10_q9: int | None = Field(default=None, ge=0, le=4)
    pss10_q10: int | None = Field(default=None, ge=0, le=4)

    # Standardized Nordic Questionnaire (NMQ) ergonomics data matrix
    nordic_nmq_data: dict | None = Field(default=None)
