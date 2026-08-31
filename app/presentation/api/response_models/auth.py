from pydantic import BaseModel
import uuid


class OrganizationMembership(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    roles: list[str]


class AuthMeResponse(BaseModel):
    email: str
    first_name: str | None = None
    last_name: str | None = None
    is_sysadmin: bool
    membership: OrganizationMembership | None
    requires_onboarding: bool


class OAuthAuthorizeResponse(BaseModel):
    authorization_url: str
