from dataclasses import dataclass
import uuid
from datetime import datetime


@dataclass
class RiskScore:
    id: uuid.UUID
    user_id: uuid.UUID
    score_name: str
    risk_level: str | None
    raw_value: float | None
    normalized_value: float | None
    explanation: str | None
    contributing_factors: dict[str, any]
    attention_flags: dict[str, bool]
    evaluated_at: datetime
    submission_id: uuid.UUID | None = None
