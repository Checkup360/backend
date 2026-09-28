import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.persistence.database import Base

if TYPE_CHECKING:
    from app.infrastructure.persistence.models.legal_document import LegalDocumentModel
    from app.infrastructure.persistence.models.user import User


class UserConsentModel(Base):
    __tablename__ = "user_consents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    consent_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    form_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("legal_documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_version: Mapped[str] = mapped_column(String(50), nullable=False)
    document_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", backref="consents")
    document: Mapped["LegalDocumentModel"] = relationship("LegalDocumentModel")

    __table_args__ = (
        Index(
            "idx_user_consents_user_active",
            "user_id",
            "consent_type",
            "form_type",
            "revoked_at",
        ),
    )
