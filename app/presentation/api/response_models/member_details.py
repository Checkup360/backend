from datetime import date

from pydantic import BaseModel


class MemberDetailsCreated(BaseModel):
    ok: bool = True


class MemberProfileResponse(BaseModel):
    first_name: str
    last_name: str
    phone_number: str | None
    date_of_birth: date
    avatar_url: str | None = None
    priority_topics: list[str] = []
