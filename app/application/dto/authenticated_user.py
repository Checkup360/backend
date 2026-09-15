import uuid
from dataclasses import dataclass

from app.domain.entities import Membership


@dataclass(frozen=True)
class AuthenticatedUser:
    id: uuid.UUID
    email: str
    is_superuser: bool
    membership: Membership | None = None
    organization_name: str | None = None
    organization_logo_url: str | None = None
