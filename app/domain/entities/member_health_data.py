import uuid
from dataclasses import dataclass, field

PHQ9_ITEM_FIELDS: tuple[str, ...] = (
    "little_interest",
    "feeling_down",
    "sleep_trouble",
    "tired_energy",
    "appetite",
    "feeling_bad",
    "concentration",
    "psychomotor",
    "self_harm_thoughts",
)


@dataclass
class MemberHealthData:
    user_id: uuid.UUID
    biological_sex: str | None = field(default=None)
    height: float | None = field(default=None)
    weight: float | None = field(default=None)
    waist_circumference: float | None = field(default=None)
    neck_circumference: float | None = field(default=None)
    snoring: bool | None = field(default=None)
    tired: bool | None = field(default=None)
    observed_apnea: bool | None = field(default=None)
    hypertension_medication: bool | None = field(default=None)
    daily_physical_activity: bool | None = field(default=None)
    fruits_vegetables: bool | None = field(default=None)
    previous_high_glucose: bool | None = field(default=None)
    family_diabetes: str | None = field(default=None)
    little_interest: int | None = field(default=None)
    feeling_down: int | None = field(default=None)
    sleep_trouble: int | None = field(default=None)
    tired_energy: int | None = field(default=None)
    appetite: int | None = field(default=None)
    feeling_bad: int | None = field(default=None)
    concentration: int | None = field(default=None)
    psychomotor: int | None = field(default=None)
    self_harm_thoughts: int | None = field(default=None)
