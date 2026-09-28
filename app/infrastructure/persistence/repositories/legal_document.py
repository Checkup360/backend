import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.legal_document import (
    LegalDocument,
    LegalDocumentStatus,
    LegalDocumentType,
)
from app.domain.repositories.legal_document import LegalDocumentRepository
from app.infrastructure.persistence.models.legal_document import LegalDocumentModel


class SQLAlchemyLegalDocumentRepository(LegalDocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_entity(model: LegalDocumentModel) -> LegalDocument:
        return LegalDocument(
            id=model.id,
            document_type=LegalDocumentType(model.document_type),
            form_type=model.form_type,
            version=model.version,
            title=model.title,
            content=model.content,
            content_hash=model.content_hash,
            status=LegalDocumentStatus(model.status),
            created_at=model.created_at,
            published_at=model.published_at,
        )

    async def get_by_id(self, document_id: uuid.UUID) -> LegalDocument | None:
        model = await self._session.get(LegalDocumentModel, document_id)
        return self._to_entity(model) if model else None

    async def get_published(
        self, document_type: LegalDocumentType, form_type: str | None = None
    ) -> LegalDocument | None:
        query = (
            select(LegalDocumentModel)
            .where(
                LegalDocumentModel.document_type == document_type.value,
                LegalDocumentModel.form_type == form_type,
                LegalDocumentModel.status == LegalDocumentStatus.PUBLISHED.value,
            )
            .order_by(
                LegalDocumentModel.published_at.desc(),
                LegalDocumentModel.created_at.desc(),
            )
        )

        result = await self._session.execute(query)
        model = result.scalars().first()
        return self._to_entity(model) if model else None

    async def get_by_type_and_version(
        self,
        document_type: LegalDocumentType,
        version: str,
        form_type: str | None = None,
    ) -> LegalDocument | None:
        query = select(LegalDocumentModel).where(
            LegalDocumentModel.document_type == document_type.value,
            LegalDocumentModel.version == version,
            LegalDocumentModel.form_type == form_type,
        )
        result = await self._session.execute(query)
        model = result.scalars().first()
        return self._to_entity(model) if model else None

    async def list_all(
        self, document_type: LegalDocumentType | None = None
    ) -> list[LegalDocument]:
        query = select(LegalDocumentModel)
        if document_type is not None:
            query = query.where(LegalDocumentModel.document_type == document_type.value)
        query = query.order_by(LegalDocumentModel.created_at.desc())

        result = await self._session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def save(self, document: LegalDocument) -> LegalDocument:
        model = await self._session.get(LegalDocumentModel, document.id)
        if model is None:
            model = LegalDocumentModel(
                id=document.id,
                document_type=document.document_type.value,
                form_type=document.form_type,
                version=document.version,
                title=document.title,
                content=document.content,
                content_hash=document.content_hash,
                status=document.status.value,
                created_at=document.created_at,
                published_at=document.published_at,
            )
            self._session.add(model)
        else:
            model.document_type = document.document_type.value
            model.form_type = document.form_type
            model.version = document.version
            model.title = document.title
            model.content = document.content
            model.content_hash = document.content_hash
            model.status = document.status.value
            model.published_at = document.published_at

        await self._session.commit()
        await self._session.refresh(model)
        return self._to_entity(model)
