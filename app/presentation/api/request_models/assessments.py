from pydantic import BaseModel, Field


class StopBangAssessmentRequest(BaseModel):
    height: float = Field(..., gt=0, description="Height in cm")
    weight: float = Field(..., gt=0, description="Weight in kg")
    neck_circumference: float = Field(..., gt=0, description="Neck circumference in cm")
    sex: str = Field(..., description="Biological sex (e.g., 'male' or 'female')")
    snoring: bool = Field(...)
    tired: bool = Field(...)
    observed_apnea: bool = Field(...)
    hypertension_medication: bool = Field(...)
