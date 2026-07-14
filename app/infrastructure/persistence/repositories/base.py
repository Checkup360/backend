from dataclasses import asdict, is_dataclass
from typing import Any, Generic, TypeVar, cast
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.database import Base

ModelType = TypeVar("ModelType", bound=Base)
DomainType = TypeVar("DomainType")


class BaseRepository(Generic[ModelType, DomainType]):
    model: type[ModelType]
    db: AsyncSession

    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    @staticmethod
    def _to_domain(orm: ModelType) -> DomainType:
        raise NotImplementedError

    def _from_domain(self, entity: DomainType) -> dict:
        if not is_dataclass(entity):
            raise TypeError("Domain entities must be dataclasses")
        return asdict(cast(Any, entity))

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
        data = self._from_domain(entity)
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
        query = delete(self.model).where(getattr(self.model, "id") == id)
        result = await self.db.execute(query)
        await self.db.commit()
        return bool(getattr(result, "rowcount", 0) > 0)
