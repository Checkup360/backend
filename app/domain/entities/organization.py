import uuid

from pydantic import BaseModel


class Organization(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    collaborators_count: int = 0
