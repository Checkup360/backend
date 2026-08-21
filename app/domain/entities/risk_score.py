from dataclasses import dataclass, field
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
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
