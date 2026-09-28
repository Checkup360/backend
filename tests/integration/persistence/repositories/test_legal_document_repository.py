from datetime import datetime, timezone
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.legal_document import (
    LegalDocument,
    LegalDocumentStatus,
    LegalDocumentType,
)
from app.infrastructure.persistence.repositories.legal_document import (
    SQLAlchemyLegalDocumentRepository,
)


@pytest.mark.asyncio
async def test_legal_document_repository_crud_and_published(db: AsyncSession):
    repo = SQLAlchemyLegalDocumentRepository(db)

    doc_draft = LegalDocument(
        id=uuid.uuid4(),
        document_type=LegalDocumentType.PRIVACY_POLICY,
        version="1.0.0",
        title="Privacy Policy v1",
        content="Draft Content",
        status=LegalDocumentStatus.DRAFT,
        created_at=datetime.now(timezone.utc),
    )
    saved_draft = await repo.save(doc_draft)
    assert saved_draft.id == doc_draft.id
    assert saved_draft.status == LegalDocumentStatus.DRAFT

    # Initially no published document
    published_initial = await repo.get_published(LegalDocumentType.PRIVACY_POLICY)
    assert published_initial is None

    # Publish document
    saved_draft.status = LegalDocumentStatus.PUBLISHED
    saved_draft.published_at = datetime.now(timezone.utc)
    updated = await repo.save(saved_draft)
    assert updated.status == LegalDocumentStatus.PUBLISHED

    # Now get_published returns it
    published = await repo.get_published(LegalDocumentType.PRIVACY_POLICY)
    assert published is not None
    assert published.id == doc_draft.id
    assert published.version == "1.0.0"

    # Get by type and version
    by_version = await repo.get_by_type_and_version(
        LegalDocumentType.PRIVACY_POLICY, "1.0.0"
    )
    assert by_version is not None
    assert by_version.id == doc_draft.id

    # Form specific document
    form_doc = LegalDocument(
        id=uuid.uuid4(),
        document_type=LegalDocumentType.FORM_CONSENT,
        form_type="biometrics",
        version="1",
        title="Biometrics Consent",
        content="Consent content",
        status=LegalDocumentStatus.PUBLISHED,
        created_at=datetime.now(timezone.utc),
        published_at=datetime.now(timezone.utc),
    )
    await repo.save(form_doc)

    published_form_doc = await repo.get_published(
        LegalDocumentType.FORM_CONSENT, form_type="biometrics"
    )
    assert published_form_doc is not None
    assert published_form_doc.form_type == "biometrics"
