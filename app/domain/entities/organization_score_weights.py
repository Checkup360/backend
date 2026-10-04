from dataclasses import dataclass
from datetime import datetime
import uuid


@dataclass(frozen=True)
class OrganizationScoreWeights:
    """
    Immutable representation of an organization's score weights and risk thresholds configuration version.
    """

    id: uuid.UUID
    organization_id: uuid.UUID
    version: int
    weights: dict[str, float]
    changed_by_user_id: uuid.UUID | None
    created_at: datetime
    risk_thresholds: dict[str, float] | None = None
