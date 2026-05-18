from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import InviteToken
from app.persistence.models.invite import InviteToken as InviteTokenORM
from app.persistence.repositories.base import BaseRepository


class InviteRepository(BaseRepository[InviteTokenORM, InviteToken]):
    def __init__(self, db: AsyncSession):
        super().__init__(InviteTokenORM, db)

    async def get_by_token(self, token: str) -> InviteToken | None:
        query = select(self.model).where(self.model.token == token)
        orm = await self.db.scalar(query)
        return self._to_domain(orm) if orm else None

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

    def _from_domain(self, entity: InviteToken) -> dict:
        return {
            "id": entity.id,
            "token": entity.token,
            "email": entity.email,
            "max_uses": entity.max_uses,
            "uses": entity.uses,
            "expires_at": entity.expires_at,
            "organization_id": entity.organization_id,
            "role": entity.role,
            "is_sysadmin": entity.is_sysadmin,
        }
