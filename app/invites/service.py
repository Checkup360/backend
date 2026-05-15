"""Lógica compartida para tokens de invitación (sin consumir)."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from app.core import settings
from app.models.invite import InviteToken
from app.models.membership import OrgRole


def build_invite_url(token: str) -> str:
    return f"{settings.frontend_url.rstrip('/')}/invite/{token}"


def build_invite_token(
    *,
    email: str | None,
    expires_in_hours: int,
    max_uses: int,
    organization_id: uuid.UUID | None = None,
    role: OrgRole | None = None,
    is_sysadmin: bool = False,
) -> InviteToken:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)
    return InviteToken(
        token=token,
        email=email,
        expires_at=expires_at,
        max_uses=max_uses,
        organization_id=organization_id,
        role=role,
        is_sysadmin=is_sysadmin,
    )
