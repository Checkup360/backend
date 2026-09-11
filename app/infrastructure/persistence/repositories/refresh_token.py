import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.refresh_token import RefreshToken as RefreshTokenEntity
from app.infrastructure.persistence.models.refresh_token import (
    RefreshToken as RefreshTokenORM,
)
from app.infrastructure.persistence.repositories.base import BaseRepository


class RefreshTokenRepositoryImpl(BaseRepository[RefreshTokenORM, RefreshTokenEntity]):
    def __init__(self, db: AsyncSession):
        super().__init__(RefreshTokenORM, db)

    @staticmethod
    def _to_domain(orm: RefreshTokenORM) -> RefreshTokenEntity:
        return RefreshTokenEntity(
            id=orm.id,
            user_id=orm.user_id,
            token_hash=orm.token_hash,
            expires_at=orm.expires_at,
            created_at=orm.created_at,
            revoked_at=orm.revoked_at,
        )

    async def create_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshTokenEntity:
        return await self.create(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

    async def get_by_token_hash(self, token_hash: str) -> RefreshTokenEntity | None:
        query = select(self.model).where(self.model.token_hash == token_hash)
        orm = await self.db.scalar(query)
        return self._to_domain(orm) if orm else None

    async def revoke(self, id: uuid.UUID) -> bool:
        now = datetime.now(timezone.utc)
        stmt = (
            update(self.model)
            .where(self.model.id == id, self.model.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return bool(getattr(result, "rowcount", 0) > 0)

    async def revoke_by_token_hash(self, token_hash: str) -> bool:
        now = datetime.now(timezone.utc)
        stmt = (
            update(self.model)
            .where(self.model.token_hash == token_hash, self.model.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return bool(getattr(result, "rowcount", 0) > 0)

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        now = datetime.now(timezone.utc)
        stmt = (
            update(self.model)
            .where(self.model.user_id == user_id, self.model.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return int(getattr(result, "rowcount", 0))
