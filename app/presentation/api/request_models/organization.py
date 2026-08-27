import re
import uuid

from pydantic import BaseModel, field_validator


class CreateOrganizationRequest(BaseModel):
    name: str
    slug: str

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("slug_required")
        value = value.strip()
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", value):
            raise ValueError("invalid_slug_format")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("name_required")
        return value.strip()


class DepartmentRequest(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_department_name(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("department_name_required")
        return value.strip()


class AssignDepartmentRequest(BaseModel):
    department_id: uuid.UUID | None = None


class ScoreWeightsRequest(BaseModel):
    score_weights: dict[str, float]

    @field_validator("score_weights")
    @classmethod
    def validate_score_weights(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("score_weights_required")
        total = 0.0
        for k, v in value.items():
            if v < 0:
                raise ValueError(f"weight_cannot_be_negative: {k}")
            total += v
        if total <= 0:
            raise ValueError("total_weights_must_be_positive")
        return value
