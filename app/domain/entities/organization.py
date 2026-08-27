import uuid
from dataclasses import dataclass, field


@dataclass
class Organization:
    id: uuid.UUID
    name: str
    slug: str
    collaborators_count: int = 0
    score_weights: dict[str, float] | None = field(default=None)
