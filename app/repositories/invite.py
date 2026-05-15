from datetime import datetime, timezone
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.invite import InviteToken
from app.repositories.base import BaseRepository


class InviteRepository(BaseRepository[InviteToken]):
    def __init__(self, db: AsyncSession):
        super().__init__(InviteToken, db)

    async def get_by_token(self, token: str) -> InviteToken | None:
        query = select(self.model).where(self.model.token == token)
        return await self.db.scalar(query)

    async def fetch_usable_invite(
        self, token: str
    ) -> tuple[InviteToken | None, str | None]:
        invite = await self.get_by_token(token)
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


async def get_invite_repository(
    db: AsyncSession = Depends(get_db),
) -> InviteRepository:
    return InviteRepository(db)
