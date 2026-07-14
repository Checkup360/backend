from dataclasses import dataclass

from app.domain.value_objects import OrgRole
from app.domain.entities.department import Department
from app.domain.entities.organization import Organization
from app.domain.entities.user import User


@dataclass
class Employee:
    user: User
    organization: Organization
    roles: list[OrgRole]
    department: Department | None = None
