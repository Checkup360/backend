from datetime import datetime
import uuid

from pydantic import BaseModel


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    collaborators_count: int
    score_weights: dict[str, float] | None = None


class ScoreWeightsResponse(BaseModel):
    score_weights: dict[str, float]


class OrganizationSummaryResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    total_members: int
    total_employees: int
    total_admins: int
    total_content_managers: int = 0


class DepartmentResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    slug: str


class OrganizationEmployeeResponse(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    roles: list[str]
    status: str
    department: DepartmentResponse | None = None
    last_assessment: datetime | None = None
