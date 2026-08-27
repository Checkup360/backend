"""Request models for modular member health forms."""

from typing import Literal
from pydantic import BaseModel, Field


class MemberFormUpdate(BaseModel):
    """Generic payload for form update endpoints."""

    # Biometrics fields
    biological_sex: Literal["M", "F"] | None = Field(default=None)
    height: float | None = Field(default=None, gt=0, lt=3)
    weight: float | None = Field(default=None, gt=0, lt=500)
    waist_circumference: float | None = Field(default=None, gt=0, lt=300)
    neck_circumference: float | None = Field(default=None, gt=0, lt=100)

    # Sleep fields
    snoring: bool | None = Field(default=None)
    tired: bool | None = Field(default=None)
    observed_apnea: bool | None = Field(default=None)

    # Habits fields
    daily_physical_activity: bool | None = Field(default=None)
    fruits_vegetables: bool | None = Field(default=None)
    hypertension_medication: bool | None = Field(default=None)
    previous_high_glucose: bool | None = Field(default=None)
    family_diabetes: Literal["no", "second_degree", "first_degree"] | None = Field(
        default=None
    )
