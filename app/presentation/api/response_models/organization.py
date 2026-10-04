from datetime import datetime
import uuid

from pydantic import BaseModel


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    collaborators_count: int
    score_weights: dict[str, float] | None = None
    risk_thresholds: dict[str, float] | None = None
    logo_url: str | None = None


class ScoreWeightsResponse(BaseModel):
    score_weights: dict[str, float]
    risk_thresholds: dict[str, float] | None = None


class OrganizationLogoResponse(BaseModel):
    logo_url: str


class OrganizationSummaryResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    total_members: int
    total_employees: int
    total_admins: int
    total_content_managers: int = 0
    logo_url: str | None = None


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
    status: str | None = None
    department: DepartmentResponse | None = None
    last_assessment: datetime | None = None
    overall_health_index: float | None = None


class SuperadminRemovalVoteResponse(BaseModel):
    id: uuid.UUID
    request_id: uuid.UUID
    voter_user_id: uuid.UUID
    decision: str
    voted_at: datetime


class SuperadminRemovalRequestResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    target_user_id: uuid.UUID
    requester_user_id: uuid.UUID
    status: str
    required_votes: int
    reason: str | None = None
    created_at: datetime
    updated_at: datetime
    votes: list[SuperadminRemovalVoteResponse]
