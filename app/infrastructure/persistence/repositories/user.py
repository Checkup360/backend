from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities import MemberDetails, User
from app.infrastructure.persistence.models.member_details import (
    MemberDetails as MemberDetailsORM,
)
from app.infrastructure.persistence.models.user import User as UserORM
from app.infrastructure.persistence.repositories.base import BaseRepository


class UserRepository(BaseRepository[UserORM, User]):
    def __init__(self, db: AsyncSession):
        super().__init__(UserORM, db)

    @staticmethod
    def _to_domain(orm: UserORM) -> User:
        return User(
            id=orm.id,
            email=orm.email,
            is_superuser=orm.is_superuser,
            is_active=orm.is_active,
        )

    def _from_domain(self, entity: User) -> dict:
        return {
            "id": entity.id,
            "email": entity.email,
            "is_superuser": entity.is_superuser,
            "is_active": entity.is_active,
        }

    async def list_sysadmins(
        self,
        search: str | None = None,
        is_active: bool | None = None,
        page: int | None = None,
        page_size: int = 10,
    ) -> tuple[list[tuple[User, MemberDetails | None]], int]:
        query = (
            select(UserORM, MemberDetailsORM)
            .outerjoin(MemberDetailsORM, MemberDetailsORM.user_id == UserORM.id)
            .where(UserORM.is_superuser.is_(True))
        )

        if is_active is not None:
            query = query.where(UserORM.is_active.is_(is_active))

        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(UserORM.email).like(term),
                    func.lower(MemberDetailsORM.first_name).like(term),
                    func.lower(MemberDetailsORM.last_name).like(term),
                )
            )

        # Count total matching
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Order by creation/email
        query = query.order_by(UserORM.email.asc())

        if page is not None and page > 0:
            query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        rows = result.unique().all()

        items: list[tuple[User, MemberDetails | None]] = []
        for user_orm, details_orm in rows:
            user = self._to_domain(user_orm)
            details = (
                MemberDetails(
                    user_id=details_orm.user_id,
                    date_of_birth=details_orm.date_of_birth,
                    first_name=details_orm.first_name,
                    last_name=details_orm.last_name,
                    phone_number=details_orm.phone_number,
                    avatar_url=details_orm.avatar_url,
                )
                if details_orm
                else None
            )
            items.append((user, details))

        return items, total

    async def count_sysadmins(self, is_active: bool | None = None) -> int:
        query = select(func.count(UserORM.id)).where(UserORM.is_superuser.is_(True))
        if is_active is not None:
            query = query.where(UserORM.is_active.is_(is_active))
        result = await self.db.execute(query)
        return result.scalar_one()
