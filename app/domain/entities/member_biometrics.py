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
