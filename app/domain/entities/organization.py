import uuid
from datetime import datetime

from pydantic import BaseModel


class Organization(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime | None = None
