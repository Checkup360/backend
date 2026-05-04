from pydantic import BaseModel
import uuid


class OrganizationMembership(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    role: str


class AuthMeResponse(BaseModel):
    email: str
    is_sysadmin: bool
    memberships: list[OrganizationMembership]


class OAuthAuthorizeResponse(BaseModel):
    authorization_url: str
