"""Lógica compartida para tokens de invitación (sin consumir)."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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


async def fetch_usable_invite(
    db: AsyncSession, token: str
) -> tuple[InviteToken | None, str | None]:
    """
    Devuelve (invite, None) si el token existe y aún no fue usado ni expiró.
    Si no aplica, (None, código de error para el cliente).
    """
    invite = await db.scalar(select(InviteToken).where(InviteToken.token == token))
    if not invite:
        return None, "invalid_invite"
    if invite.is_exhausted:
        return None, "invite_used"
    expires_at = invite.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        return None, "invite_expired"
    return invite, None
