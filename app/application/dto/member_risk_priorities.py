import uuid
from dataclasses import dataclass, field

from app.application.dto.content_category import ContentCategoryDTO


@dataclass(frozen=True)
class MemberRiskPrioritiesDTO:
    user_id: uuid.UUID
    risk_weights: dict[str, float]
    highest_risk: str | None
    categories: list[ContentCategoryDTO] = field(default_factory=list)
