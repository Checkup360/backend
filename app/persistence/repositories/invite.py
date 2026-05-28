from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities import InviteToken
from app.persistence.models.invite import InviteToken as InviteTokenORM
from app.persistence.repositories.base import BaseRepository


def _organization_from_orm(orm: InviteTokenORM):
    if orm.organization_id is None:
        return None
    try:
        from app.domain.entities import Organization

        return Organization(
            id=orm.organization.id,
            name=orm.organization.name,
            slug=orm.organization.slug,
        )
    except Exception:
        return None


class InviteRepository(BaseRepository[InviteTokenORM, InviteToken]):
    def __init__(self, db: AsyncSession):
        super().__init__(InviteTokenORM, db)

    async def get(self, id) -> InviteToken | None:
        query = (
            select(self.model)
            .options(selectinload(self.model.organization))
            .where(self.model.id == id)
        )
        orm = await self.db.scalar(query)
        return self._to_domain(orm) if orm else None

    async def get_by_token(self, token: str) -> InviteToken | None:
        query = (
            select(self.model)
            .options(selectinload(self.model.organization))
            .where(self.model.token == token)
        )
        orm = await self.db.scalar(query)
        return self._to_domain(orm) if orm else None

    @staticmethod
    def _to_domain(orm: InviteTokenORM) -> InviteToken:
        role = None
        if orm.role is not None:
            from app.domain.entities.org_role import OrgRole

            role = orm.role if isinstance(orm.role, OrgRole) else OrgRole(orm.role)

        return InviteToken(
            id=orm.id,
            token=orm.token,
            email=orm.email,
            max_uses=orm.max_uses,
            uses=orm.uses,
            expires_at=orm.expires_at,
            organization_id=orm.organization_id,
            role=role,
            is_sysadmin=orm.is_sysadmin,
            organization=_organization_from_orm(orm),
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
