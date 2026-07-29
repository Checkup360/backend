import re
from datetime import date

from pydantic import BaseModel, field_validator

_PHONE_RE = re.compile(r"^\+[\d\s\-(). ]{7,19}$")


class MemberDetailsCreate(BaseModel):
    date_of_birth: date
    first_name: str = ""
    last_name: str = ""
    phone_number: str

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("date_of_birth_in_future")
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


class MemberProfileUpdate(BaseModel):
    first_name: str
    last_name: str
    phone_number: str | None = None

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
