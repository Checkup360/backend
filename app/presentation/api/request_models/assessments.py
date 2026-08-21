from pydantic import BaseModel, Field


class ClinicalAssessmentRequest(BaseModel):
    age: int | None = Field(None, gt=0, description="Age in years")
    height: float | None = Field(None, gt=0, description="Height in cm")
    weight: float | None = Field(None, gt=0, description="Weight in kg")
    waist_circumference: float | None = Field(
        None, gt=0, description="Waist circumference in cm"
    )
    neck_circumference: float | None = Field(
        None, gt=0, description="Neck circumference in cm"
    )
    sex: str | None = Field(
        None, description="Biological sex (e.g., 'male' or 'female')"
    )
    snoring: bool | None = Field(None)
    tired: bool | None = Field(None)
    observed_apnea: bool | None = Field(None)
    hypertension_medication: bool | None = Field(None)
    daily_physical_activity: bool | None = Field(None)
    fruits_vegetables: bool | None = Field(None)
    previous_high_glucose: bool | None = Field(None)
    family_diabetes: str | None = Field(
        None, description="no, yes_2nd_degree, or yes_1st_degree"
    )
