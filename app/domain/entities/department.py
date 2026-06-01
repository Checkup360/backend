import uuid
from datetime import datetime

from pydantic import BaseModel


class Department(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    slug: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
