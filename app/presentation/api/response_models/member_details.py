import uuid
from datetime import date

from pydantic import BaseModel

from app.presentation.api.response_models.content_category import (
    ContentCategoryResponse,
)


class MemberDetailsCreated(BaseModel):
    ok: bool = True


class MemberProfileResponse(BaseModel):
    first_name: str
    last_name: str
    phone_number: str | None
    date_of_birth: date
    avatar_url: str | None = None
    priority_topics: list[str] = []


class MemberRiskPrioritiesResponse(BaseModel):
    user_id: uuid.UUID
    risk_weights: dict[str, float]
    highest_risk: str | None = None
    categories: list[ContentCategoryResponse] = []


class AvatarUploadResponse(BaseModel):
    avatar_url: str
