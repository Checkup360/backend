import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class MemberRiskPrioritiesDTO:
    user_id: uuid.UUID
    risk_weights: dict[str, float]
    highest_risk: str | None
