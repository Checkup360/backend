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
