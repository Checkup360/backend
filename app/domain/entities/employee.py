from pydantic import BaseModel

from app.domain.entities.org_role import OrgRole
from app.domain.entities.organization import Organization
from app.domain.entities.user import User


class Employee(BaseModel):
    user: User
    organization: Organization
    roles: list[OrgRole]
