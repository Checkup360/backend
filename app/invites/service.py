"""Lógica compartida para tokens de invitación (sin consumir)."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invite import InviteToken


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
