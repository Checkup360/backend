import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Department:
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    slug: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
