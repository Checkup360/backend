import re
import uuid

from pydantic import BaseModel, Field, field_validator

from typing import Literal

from app.domain.value_objects import OrgRole


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
    risk_thresholds: dict[str, float] | None = None

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

    @field_validator("risk_thresholds")
    @classmethod
    def validate_risk_thresholds(
        cls, value: dict[str, float] | None
    ) -> dict[str, float] | None:
        if value is None:
            return None
        if "low" not in value or "moderate" not in value:
            raise ValueError("risk_thresholds_must_contain_low_and_moderate")
        low = float(value["low"])
        moderate = float(value["moderate"])
        if not (0.0 <= moderate < low <= 100.0):
            raise ValueError("invalid_risk_threshold_ranges")
        return value


class UpdateOrganizationRequest(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("name_required")
        return value.strip()


class UpdateEmployeeRolesRequest(BaseModel):
    roles: list[OrgRole]


class CreateSuperadminRemovalRequest(BaseModel):
    reason: str | None = Field(None, max_length=500)


class VoteSuperadminRemovalRequest(BaseModel):
    decision: Literal["approve", "reject"]
