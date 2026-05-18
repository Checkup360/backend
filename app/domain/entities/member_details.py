import uuid
from datetime import date

from pydantic import BaseModel


class MemberDetails(BaseModel):
    user_id: uuid.UUID
    date_of_birth: date
