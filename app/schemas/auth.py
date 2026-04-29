from pydantic import BaseModel


class AuthMeResponse(BaseModel):
    email: str


class OAuthAuthorizeResponse(BaseModel):
    authorization_url: str
