from pydantic import BaseModel, Field


class ClinicalAssessmentRequest(BaseModel):
    age: int | None = Field(None, gt=0, description="Age in years")
    height: float | None = Field(None, gt=0, description="Height in cm")
    weight: float | None = Field(None, gt=0, description="Weight in kg")
    waist_circumference: float | None = Field(
        None, gt=0, description="Waist circumference in cm"
    )
    triglycerides: float | None = Field(
        None, ge=0, description="Triglycerides in mg/dL"
    )
    total_cholesterol: float | None = Field(
        None, ge=0, description="Total cholesterol in mg/dL"
    )
    hdl_cholesterol: float | None = Field(
        None, ge=0, description="HDL cholesterol in mg/dL"
    )
    systolic_blood_pressure: float | None = Field(
        None, gt=0, description="Systolic blood pressure in mmHg"
    )
    diastolic_blood_pressure: float | None = Field(
        None, gt=0, description="Diastolic blood pressure in mmHg"
    )
    fasting_glucose: float | None = Field(
        None, ge=0, description="Fasting glucose in mg/dL"
    )
    glucose_lowering_medication: bool | None = Field(None)
    neck_circumference: float | None = Field(
        None, gt=0, description="Neck circumference in cm"
    )
    sex: str | None = Field(
        None, description="Biological sex (e.g., 'male' or 'female')"
    )
    snoring: bool | None = Field(None)
    tired: bool | None = Field(None)
    observed_apnea: bool | None = Field(None)
    smoker: bool | None = Field(None, description="Current smoking status")
    hypertension_medication: bool | None = Field(None)
    daily_physical_activity: bool | None = Field(None)
    fruits_vegetables: bool | None = Field(None)
    previous_high_glucose: bool | None = Field(None)
    family_diabetes: str | None = Field(
        None, description="no, yes_2nd_degree, or yes_1st_degree"
    )
    little_interest: int | None = Field(None, ge=0, le=3)
    feeling_down: int | None = Field(None, ge=0, le=3)
    sleep_trouble: int | None = Field(None, ge=0, le=3)
    tired_energy: int | None = Field(None, ge=0, le=3)
    appetite: int | None = Field(None, ge=0, le=3)
    feeling_bad: int | None = Field(None, ge=0, le=3)
    concentration: int | None = Field(None, ge=0, le=3)
    psychomotor: int | None = Field(None, ge=0, le=3)
    self_harm_thoughts: int | None = Field(None, ge=0, le=3)
    eoss_physical_health_stage: int | None = Field(None, ge=0, le=4)
    eoss_mental_health_stage: int | None = Field(None, ge=0, le=4)
    eoss_functional_stage: int | None = Field(None, ge=0, le=4)
