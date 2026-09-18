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
    triglycerides: float | None = field(default=None)
    total_cholesterol: float | None = field(default=None)
    hdl_cholesterol: float | None = field(default=None)
    systolic_blood_pressure: float | None = field(default=None)
    diastolic_blood_pressure: float | None = field(default=None)
    fasting_glucose: float | None = field(default=None)
    glucose_lowering_medication: bool | None = field(default=None)
    neck_circumference: float | None = field(default=None)
    snoring: bool | None = field(default=None)
    tired: bool | None = field(default=None)
    observed_apnea: bool | None = field(default=None)
    smoker: bool | None = field(default=None)
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
    eoss_physical_health_stage: int | None = field(default=None)
    eoss_mental_health_stage: int | None = field(default=None)
    eoss_functional_stage: int | None = field(default=None)
    statins: bool | None = field(default=None)
    lab_study_date: str | None = field(default=None)
    nordic_nmq_data: dict | None = field(default=None)
    audit_c_frequency: int | None = field(default=None)
    audit_c_quantity: int | None = field(default=None)
    audit_c_heavy_drinking: int | None = field(default=None)
    pss10_q1: int | None = field(default=None)
    pss10_q2: int | None = field(default=None)
    pss10_q3: int | None = field(default=None)
    pss10_q4: int | None = field(default=None)
    pss10_q5: int | None = field(default=None)
    pss10_q6: int | None = field(default=None)
    pss10_q7: int | None = field(default=None)
    pss10_q8: int | None = field(default=None)
    pss10_q9: int | None = field(default=None)
    pss10_q10: int | None = field(default=None)
