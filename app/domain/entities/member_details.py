import uuid
from dataclasses import dataclass
from datetime import date


@dataclass
class MemberDetails:
    user_id: uuid.UUID
    date_of_birth: date
