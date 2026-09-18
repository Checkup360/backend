from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass(frozen=True)
class MemberOverallScore:
    id: uuid.UUID
    user_id: uuid.UUID
    organization_id: uuid.UUID
    score_weights_id: uuid.UUID
    overall_score: float
    risk_level: str
    evaluated_at: datetime
    submission_id: uuid.UUID | None = None
