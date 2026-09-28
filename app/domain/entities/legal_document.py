from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import uuid


class LegalDocumentType(str, Enum):
    TERMS_AND_CONDITIONS = "TERMS_AND_CONDITIONS"
    PRIVACY_POLICY = "PRIVACY_POLICY"
    HEALTH_DATA_PROCESSING_CONSENT = "HEALTH_DATA_PROCESSING_CONSENT"
    FORM_CONSENT = "FORM_CONSENT"


class LegalDocumentStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


@dataclass
class LegalDocument:
    id: uuid.UUID
    document_type: LegalDocumentType
    version: str
    title: str
    content: str
    status: LegalDocumentStatus
    created_at: datetime
    form_type: str | None = None
    content_hash: str | None = None
    published_at: datetime | None = None
