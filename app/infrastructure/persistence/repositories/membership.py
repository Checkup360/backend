import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.domain.entities import Employee, Membership
from app.domain.entities.department import Department
from app.domain.value_objects.org_role import OrgRole
from app.domain.entities.organization import Organization
from app.domain.entities.user import User
from app.infrastructure.persistence.models.membership import Membership as MembershipORM
from app.infrastructure.persistence.models.user import User as UserORM
from app.infrastructure.persistence.repositories.base import BaseRepository


class MembershipRepository(BaseRepository[MembershipORM, Membership]):
    def __init__(self, db: AsyncSession):
        super().__init__(MembershipORM, db)

    async def get_by_user(self, user_id: uuid.UUID) -> Membership | None:
        query = select(self.model).where(self.model.user_id == user_id)
        result = await self.db.execute(query)
        orm = result.scalars().first()
        return self._to_domain(orm) if orm else None

    async def get_by_user_and_org(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Membership | None:
        query = select(self.model).where(
            self.model.user_id == user_id,
            self.model.organization_id == organization_id,
        )
        result = await self.db.execute(query)
        orm = result.scalars().first()
        return self._to_domain(orm) if orm else None

    async def is_admin_of_any(self, user_id: uuid.UUID) -> bool:
        query = select(self.model).where(
            self.model.user_id == user_id,
            self.model.roles.contains([OrgRole.ADMIN]),
        )
        result = await self.db.execute(query)
        return result.first() is not None

    async def get_admin_organization_id(self, user_id: uuid.UUID) -> uuid.UUID | None:
        query = (
            select(self.model.organization_id)
            .where(
                self.model.user_id == user_id,
                self.model.roles.contains([OrgRole.ADMIN]),
            )
            .limit(1)
        )
        return await self.db.scalar(query)

    async def list_members_for_organization(
        self, organization_id: uuid.UUID, roles: list[OrgRole] | None = None
    ) -> list[Employee]:
        role_filters = (
            [self.model.roles.contains([role]) for role in roles] if roles else []
        )
        query = (
            select(self.model)
            .join(UserORM, UserORM.id == self.model.user_id)  # pyright: ignore[reportArgumentType]
            .options(joinedload(self.model.user), joinedload(self.model.organization))
            .where(self.model.organization_id == organization_id)
            .order_by(UserORM.email)
        )
        if role_filters:
            query = query.where(or_(*role_filters))
        result = await self.db.scalars(query)
        return [self._to_employee(orm) for orm in result.unique().all()]

    async def get_employee(
        self, user_id: uuid.UUID, organization_id: uuid.UUID
    ) -> Employee | None:
        query = (
            select(self.model)
            .join(UserORM, UserORM.id == self.model.user_id)  # pyright: ignore[reportArgumentType]
            .options(
                joinedload(self.model.user),
                joinedload(self.model.organization),
                joinedload(self.model.department),
            )
            .where(
                self.model.user_id == user_id,
                self.model.organization_id == organization_id,
            )
        )
        orm = await self.db.scalar(query)
        return self._to_employee(orm) if orm else None

    async def count_members_for_organization(
        self, organization_id: uuid.UUID, roles: list[OrgRole] | None = None
    ) -> int:
        role_filters = (
            [self.model.roles.contains([role]) for role in roles] if roles else []
        )
        query = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.organization_id == organization_id)
        )
        if role_filters:
            query = query.where(or_(*role_filters))
        return await self.db.scalar(query) or 0

    async def count_superadmins(self, organization_id: uuid.UUID) -> int:
        query = (
            select(func.count())
            .select_from(self.model)
            .where(
                self.model.organization_id == organization_id,
                self.model.roles.contains([OrgRole.SUPERADMIN]),
            )
        )
        return await self.db.scalar(query) or 0

    async def save(self, entity: Membership) -> Membership:
        data = self._from_domain(entity)

        query = select(self.model).where(
            self.model.user_id == data["user_id"],
            self.model.organization_id == data["organization_id"],
        )
        result = await self.db.execute(query)
        orm = result.scalars().first()

        if orm is not None:
            roles = [r if isinstance(r, OrgRole) else OrgRole(r) for r in data["roles"]]
            orm.roles = roles
            orm.department_id = data["department_id"]
            await self.db.commit()
            await self.db.refresh(orm)
            return self._to_domain(orm)
        return await self.create(**data)

    @staticmethod
    def _to_domain(orm: MembershipORM) -> Membership:
        roles = [r if isinstance(r, OrgRole) else OrgRole(r) for r in orm.roles]
        return Membership(
            user_id=orm.user_id,
            organization_id=orm.organization_id,
            roles=roles,
            department_id=orm.department_id,
        )

    @staticmethod
    def _to_employee(orm: MembershipORM) -> Employee:
        roles = [r if isinstance(r, OrgRole) else OrgRole(r) for r in orm.roles]
        return Employee(
            user=User(
                id=orm.user.id,
                email=orm.user.email,
                is_superuser=orm.user.is_superuser,
                is_active=orm.user.is_active,
            ),
            organization=Organization(
                id=orm.organization.id,
                name=orm.organization.name,
                slug=orm.organization.slug,
            ),
            roles=roles,
            department=(
                Department(
                    id=orm.department.id,
                    organization_id=orm.department.organization_id,
                    name=orm.department.name,
                    slug=orm.department.slug,
                    created_at=orm.department.created_at,
                    updated_at=orm.department.updated_at,
                )
                if orm.department
                else None
            ),
        )

    def _from_domain(self, entity: Membership) -> dict:
        return {
            "user_id": entity.user_id,
            "organization_id": entity.organization_id,
            "roles": [r.value if isinstance(r, OrgRole) else r for r in entity.roles],
            "department_id": entity.department_id,
        }
