from abc import ABC, abstractmethod
import uuid

from app.domain.entities.legal_document import (
    LegalDocument,
    LegalDocumentType,
)


class LegalDocumentRepository(ABC):
    """Domain repository interface for versioned legal documents."""

    @abstractmethod
    async def get_by_id(self, document_id: uuid.UUID) -> LegalDocument | None:
        pass

    @abstractmethod
    async def get_published(
        self, document_type: LegalDocumentType, form_type: str | None = None
    ) -> LegalDocument | None:
        """Returns the currently published version of the requested document."""
        pass

    @abstractmethod
    async def get_by_type_and_version(
        self,
        document_type: LegalDocumentType,
        version: str,
        form_type: str | None = None,
    ) -> LegalDocument | None:
        pass

    @abstractmethod
    async def list_all(
        self, document_type: LegalDocumentType | None = None
    ) -> list[LegalDocument]:
        pass

    @abstractmethod
    async def save(self, document: LegalDocument) -> LegalDocument:
        pass
