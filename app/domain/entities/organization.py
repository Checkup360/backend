import uuid
from dataclasses import dataclass


@dataclass
class Organization:
    id: uuid.UUID
    name: str
    slug: str
    collaborators_count: int = 0
