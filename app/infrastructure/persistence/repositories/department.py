import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.department import Department
from app.infrastructure.persistence.models.department import Department as DepartmentORM
from app.infrastructure.persistence.models.membership import Membership
from app.infrastructure.persistence.repositories.base import BaseRepository


class DepartmentRepository(BaseRepository[DepartmentORM, Department]):
    def __init__(self, db: AsyncSession):
        super().__init__(DepartmentORM, db)

    async def list_by_organization(
        self, organization_id: uuid.UUID
    ) -> list[Department]:
        result = await self.db.scalars(
            select(self.model)
            .where(self.model.organization_id == organization_id)
            .order_by(self.model.name)
        )
        return [self._to_domain(orm) for orm in result.all()]

    async def get_by_organization(
        self, organization_id: uuid.UUID, department_id: uuid.UUID
    ) -> Department | None:
        orm = await self.db.scalar(
            select(self.model).where(
                self.model.id == department_id,
                self.model.organization_id == organization_id,
            )
        )
        return self._to_domain(orm) if orm else None

    async def get_by_organization_and_slug(
        self, organization_id: uuid.UUID, slug: str
    ) -> Department | None:
        orm = await self.db.scalar(
            select(self.model).where(
                self.model.organization_id == organization_id,
                self.model.slug == slug,
            )
        )
        return self._to_domain(orm) if orm else None

    async def count_memberships(self, department_id: uuid.UUID) -> int:
        return (
            await self.db.scalar(
                select(func.count())
                .select_from(Membership)
                .where(Membership.department_id == department_id)
            )
            or 0
        )

    async def delete_by_organization(
        self, organization_id: uuid.UUID, department_id: uuid.UUID
    ) -> bool:
        result = await self.db.execute(
            delete(self.model).where(
                self.model.id == department_id,
                self.model.organization_id == organization_id,
            )
        )
        await self.db.commit()
        return bool(getattr(result, "rowcount", 0) > 0)

    @staticmethod
    def _to_domain(orm: DepartmentORM) -> Department:
        return Department(
            id=orm.id,
            organization_id=orm.organization_id,
            name=orm.name,
            slug=orm.slug,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def _from_domain(self, entity: Department) -> dict:
        return {
            "id": entity.id,
            "organization_id": entity.organization_id,
            "name": entity.name,
            "slug": entity.slug,
        }
