import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.entities import Department, InviteToken
from app.domain.value_objects import OrgRole
from app.infrastructure.persistence.models.invite import InviteToken as InviteTokenORM
from app.infrastructure.persistence.repositories.base import BaseRepository


def _organization_from_orm(orm: InviteTokenORM):
    if orm.organization_id is None:
        return None
    org = orm.__dict__.get("organization")
    if org is None:
        return None
    from app.domain.entities import Organization

    return Organization(
        id=org.id,
        name=org.name,
        slug=org.slug,
    )


def _department_from_orm(orm: InviteTokenORM) -> Department | None:
    dept = orm.__dict__.get("department")
    if dept is None:
        return None
    return Department(
        id=dept.id,
        organization_id=dept.organization_id,
        name=dept.name,
        slug=dept.slug,
        created_at=dept.created_at,
        updated_at=dept.updated_at,
    )


class InviteRepository(BaseRepository[InviteTokenORM, InviteToken]):
    def __init__(self, db: AsyncSession):
        super().__init__(InviteTokenORM, db)

    async def get(self, id) -> InviteToken | None:
        query = (
            select(self.model)
            .options(
                selectinload(self.model.organization),
                selectinload(self.model.department),
            )
            .where(self.model.id == id)
        )
        orm = await self.db.scalar(query)
        return self._to_domain(orm) if orm else None

    async def get_by_token(self, token: str) -> InviteToken | None:
        query = (
            select(self.model)
            .options(
                selectinload(self.model.organization),
                selectinload(self.model.department),
            )
            .where(self.model.token == token)
        )
        orm = await self.db.scalar(query)
        return self._to_domain(orm) if orm else None

    @staticmethod
    def _to_domain(orm: InviteTokenORM) -> InviteToken:
        role = None
        if orm.role is not None:
            from app.domain.value_objects.org_role import OrgRole

            role = orm.role if isinstance(orm.role, OrgRole) else OrgRole(orm.role)

        return InviteToken(
            id=orm.id,
            token=orm.token,
            email=orm.email,
            max_uses=orm.max_uses,
            uses=orm.uses,
            expires_at=orm.expires_at,
            organization_id=orm.organization_id,
            department_id=orm.department_id,
            role=role,
            is_sysadmin=orm.is_sysadmin,
            organization=_organization_from_orm(orm),
            department=_department_from_orm(orm),
        )

    async def list_filtered(
        self,
        *,
        organization_id: uuid.UUID | None,
        is_sysadmin: bool,
        role: OrgRole | None,
        status: str | None,
        page: int | None,
        page_size: int,
    ) -> tuple[list[InviteToken], int]:
        query = select(self.model).options(
            selectinload(self.model.organization),
            selectinload(self.model.department),
        )
        query = query.where(self.model.is_sysadmin.is_(is_sysadmin))
        if organization_id is not None:
            query = query.where(self.model.organization_id == organization_id)
        if role is not None:
            query = query.where(self.model.role == role)
        if status is not None:
            now = datetime.now(timezone.utc)
            if status == "used":
                query = query.where(self.model.uses >= self.model.max_uses)
            elif status == "expired":
                query = query.where(
                    self.model.uses < self.model.max_uses,
                    self.model.expires_at <= now,
                )
            elif status == "active":
                query = query.where(
                    self.model.uses < self.model.max_uses,
                    self.model.expires_at > now,
                )

        count_query = select(func.count()).select_from(query.order_by(None).subquery())
        total = await self.db.scalar(count_query) or 0
        query = query.order_by(self.model.created_at.desc())
        if page is not None:
            query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.scalars(query)
        return [self._to_domain(orm) for orm in result.all()], total

    async def delete_filtered(
        self,
        *,
        ids: list[uuid.UUID],
        is_sysadmin: bool,
        organization_id: uuid.UUID | None,
    ) -> int:
        filters: list[Any] = [
            self.model.id.in_(ids),
            self.model.is_sysadmin.is_(is_sysadmin),
        ]
        if organization_id is not None:
            filters.append(self.model.organization_id == organization_id)
        result = await self.db.execute(delete(self.model).where(*filters))
        await self.db.commit()
        return getattr(result, "rowcount", 0) or 0

    def _from_domain(self, entity: InviteToken) -> dict:
        return {
            "id": entity.id,
            "token": entity.token,
            "email": entity.email,
            "max_uses": entity.max_uses,
            "uses": entity.uses,
            "expires_at": entity.expires_at,
            "organization_id": entity.organization_id,
            "department_id": entity.department_id,
            "role": entity.role,
            "is_sysadmin": entity.is_sysadmin,
        }
