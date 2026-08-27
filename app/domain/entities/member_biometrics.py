import uuid
from dataclasses import dataclass, field


@dataclass
class MemberBiometrics:
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
