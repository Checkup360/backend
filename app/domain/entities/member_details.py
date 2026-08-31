import uuid
from dataclasses import dataclass, field
from datetime import date


@dataclass
class MemberDetails:
    user_id: uuid.UUID
    date_of_birth: date
    first_name: str = field(default="")
    last_name: str = field(default="")
    phone_number: str | None = field(default=None)
    avatar_url: str | None = field(default=None)
