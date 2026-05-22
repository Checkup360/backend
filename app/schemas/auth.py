from pydantic import BaseModel
import uuid


class OrganizationMembership(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    roles: list[str]


class AuthMeResponse(BaseModel):
    email: str
    is_sysadmin: bool
    memberships: list[OrganizationMembership]
    requires_onboarding: bool


class OAuthAuthorizeResponse(BaseModel):
    authorization_url: str
