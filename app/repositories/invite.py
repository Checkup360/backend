from datetime import datetime, timezone

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domain.entities import InviteToken
from app.models.invite import InviteToken as InviteTokenORM
from app.repositories.base import BaseRepository


class InviteRepository(BaseRepository[InviteTokenORM, InviteToken]):
    def __init__(self, db: AsyncSession):
        super().__init__(InviteTokenORM, db)

    async def get_by_token(self, token: str) -> InviteToken | None:
        query = select(self.model).where(self.model.token == token)
        orm = await self.db.scalar(query)
        return self._to_domain(orm) if orm else None

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

    @staticmethod
    def _to_domain(orm: InviteTokenORM) -> InviteToken:
        return InviteToken(
            id=orm.id,
            token=orm.token,
            email=orm.email,
            max_uses=orm.max_uses,
            uses=orm.uses,
            expires_at=orm.expires_at,
            organization_id=orm.organization_id,
            role=orm.role,
            is_sysadmin=orm.is_sysadmin,
        )


async def get_invite_repository(
    db: AsyncSession = Depends(get_db),
) -> InviteRepository:
    return InviteRepository(db)
