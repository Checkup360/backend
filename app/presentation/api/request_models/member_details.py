from datetime import date

from pydantic import BaseModel, field_validator


class MemberDetailsCreate(BaseModel):
    date_of_birth: date

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("date_of_birth_in_future")
        return value
