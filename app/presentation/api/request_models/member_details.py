import re
from datetime import date
from urllib.parse import urlparse

from pydantic import BaseModel, field_validator

_PHONE_RE = re.compile(r"^\+[\d\s\-(). ]{7,19}$")


class MemberDetailsCreate(BaseModel):
    date_of_birth: date
    first_name: str = ""
    last_name: str = ""
    phone_number: str | None = None
    avatar_url: str | None = None

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date) -> date:
        today = date.today()
        if value > today:
            raise ValueError("date_of_birth_in_future")
        age = (
            today.year
            - value.year
            - ((today.month, today.day) < (value.month, value.day))
        )
        if age < 18:
            raise ValueError("minimum_age_required_18")
        return value

    @field_validator("phone_number", mode="before")
    @classmethod
    def validate_phone_number(cls, value: object) -> str | None:
        if value is None or value == "":
            return None
        if not isinstance(value, str):
            raise ValueError("invalid_phone_number")
        stripped = value.strip()
        if not _PHONE_RE.match(stripped):
            raise ValueError("invalid_phone_number")
        return stripped

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        if stripped.lower().startswith("data:"):
            raise ValueError("base64_avatar_not_allowed")
        parsed = urlparse(stripped)
        if parsed.scheme in ("http", "https") and parsed.path.startswith("/media/"):
            return parsed.path
        return stripped


class MemberProfileUpdate(BaseModel):
    first_name: str
    last_name: str
    phone_number: str | None = None
    date_of_birth: date
    avatar_url: str | None = None

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date) -> date:
        today = date.today()
        if value > today:
            raise ValueError("date_of_birth_in_future")
        age = (
            today.year
            - value.year
            - ((today.month, today.day) < (value.month, value.day))
        )
        if age < 18:
            raise ValueError("minimum_age_required_18")
        return value

    @field_validator("phone_number", mode="before")
    @classmethod
    def validate_phone_number(cls, value: object) -> str | None:
        if value is None or value == "":
            return None
        if not isinstance(value, str):
            raise ValueError("invalid_phone_number")
        stripped = value.strip()
        if not _PHONE_RE.match(stripped):
            raise ValueError("invalid_phone_number")
        return stripped

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        if stripped.lower().startswith("data:"):
            raise ValueError("base64_avatar_not_allowed")
        parsed = urlparse(stripped)
        if parsed.scheme in ("http", "https") and parsed.path.startswith("/media/"):
            return parsed.path
        return stripped
