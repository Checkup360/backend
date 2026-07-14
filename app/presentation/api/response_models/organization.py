import uuid

from pydantic import BaseModel


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    collaborators_count: int


class OrganizationSummaryResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    total_members: int
    total_employees: int
    total_admins: int


class DepartmentResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    slug: str


class OrganizationEmployeeResponse(BaseModel):
    id: uuid.UUID
    email: str
    roles: list[str]
    status: str
    department: DepartmentResponse | None = None
