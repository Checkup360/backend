"""DTOs for interacting with the external Risk Scoring Engine."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HealthDataDTO:
    """Input data for risk scoring."""

    age: int | None = None
    sex: str | None = None
    weight: float | None = None
    height: float | None = None
    waist_circumference: float | None = None
    systolic_blood_pressure: float | None = None
    total_cholesterol: float | None = None
    hdl: float | None = None
    triglycerides: float | None = None
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


@dataclass(frozen=True)
class ScoreResultDTO:
    """Result of a computed risk score from the engine."""

    score_id: str
    score_name: str
    domain: str
    status: str
    raw_value: float | None = None
    normalized_value: float | None = None
    risk_level: str | None = None
    explanation: str | None = None
    contributing_factors: dict[str, Any] = field(default_factory=dict)
    attention_flags: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoreCatalogItemDTO:
    """Metadata for an available risk score calculator from the engine."""

    score_id: str
    score_name: str
    domain: str
    required_fields: list[str] = field(default_factory=list)
    optional_fields: list[str] = field(default_factory=list)
