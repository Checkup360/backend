from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base

ModelType = TypeVar("ModelType", bound=Base)
DomainType = TypeVar("DomainType")


class BaseRepository(Generic[ModelType, DomainType]):
    model: type[ModelType]
    db: AsyncSession

    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    def _to_domain(self, orm: ModelType) -> DomainType:
        raise NotImplementedError

    async def get(self, id: UUID) -> DomainType | None:
        orm = await self.db.get(self.model, id)
        return self._to_domain(orm) if orm else None

    async def list(self) -> list[DomainType]:
        result = await self.db.scalars(select(self.model))
        return [self._to_domain(o) for o in result.all()]

    async def create(self, **kwargs) -> DomainType:
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return self._to_domain(instance)

    async def update(self, id: UUID, **kwargs) -> DomainType | None:
        orm = await self.db.get(self.model, id)
        if orm is None:
            return None
        for key, value in kwargs.items():
            setattr(orm, key, value)
        await self.db.commit()
        await self.db.refresh(orm)
        return self._to_domain(orm)

    async def save(self, entity: DomainType) -> DomainType:
        data = entity.model_dump()
        pk_value = data.get("id")
        if pk_value:
            orm = await self.db.get(self.model, pk_value)
            if orm is not None:
                for key, value in data.items():
                    setattr(orm, key, value)
                await self.db.commit()
                await self.db.refresh(orm)
                return self._to_domain(orm)
        orm = self.model(**data)
        self.db.add(orm)
        await self.db.commit()
        await self.db.refresh(orm)
        return self._to_domain(orm)

    async def delete(self, id: UUID) -> bool:
        query = delete(self.model).where(self.model.id == id)
        result = await self.db.execute(query)
        await self.db.commit()
        return result.rowcount > 0
