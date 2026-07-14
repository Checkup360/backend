import uuid
from dataclasses import dataclass

from app.domain.value_objects import OrgRole


@dataclass
class Membership:
    user_id: uuid.UUID
    organization_id: uuid.UUID
    roles: list[OrgRole]
    department_id: uuid.UUID | None = None
