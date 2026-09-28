"""add legal documents and user consents tables and consent_id to submissions

Revision ID: e5a6c7d8e9f0
Revises: f1a8b9c0d2e3
Create Date: 2026-09-28 18:15:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e5a6c7d8e9f0"
down_revision: Union[str, Sequence[str], None] = "8ac63147e547"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create legal_documents table
    op.create_table(
        "legal_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column("document_type", sa.String(length=100), nullable=False),
        sa.Column("form_type", sa.String(length=100), nullable=True),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=True),
        sa.Column(
            "status", sa.String(length=50), nullable=False, server_default="DRAFT"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_legal_documents_document_type",
        "legal_documents",
        ["document_type"],
        unique=False,
    )
    op.create_index(
        "ix_legal_documents_form_type",
        "legal_documents",
        ["form_type"],
        unique=False,
    )
    op.create_index(
        "ix_legal_documents_status",
        "legal_documents",
        ["status"],
        unique=False,
    )
    op.create_index(
        "uq_legal_documents_type_form_version",
        "legal_documents",
        ["document_type", "form_type", "version"],
        unique=True,
    )

    # 2. Create user_consents table
    op.create_table(
        "user_consents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("consent_type", sa.String(length=100), nullable=False),
        sa.Column("form_type", sa.String(length=100), nullable=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("legal_documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("document_version", sa.String(length=50), nullable=False),
        sa.Column("document_hash", sa.String(length=128), nullable=True),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
    )
    op.create_index(
        "ix_user_consents_user_id", "user_consents", ["user_id"], unique=False
    )
    op.create_index(
        "ix_user_consents_consent_type",
        "user_consents",
        ["consent_type"],
        unique=False,
    )
    op.create_index(
        "ix_user_consents_form_type",
        "user_consents",
        ["form_type"],
        unique=False,
    )
    op.create_index(
        "ix_user_consents_document_id",
        "user_consents",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_consents_revoked_at",
        "user_consents",
        ["revoked_at"],
        unique=False,
    )
    op.create_index(
        "idx_user_consents_user_active",
        "user_consents",
        ["user_id", "consent_type", "form_type", "revoked_at"],
        unique=False,
    )

    # 3. Add consent_id to assessment_submissions table
    op.add_column(
        "assessment_submissions",
        sa.Column(
            "consent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user_consents.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_assessment_submissions_consent_id",
        "assessment_submissions",
        ["consent_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assessment_submissions_consent_id", table_name="assessment_submissions"
    )
    op.drop_column("assessment_submissions", "consent_id")

    op.drop_index("idx_user_consents_user_active", table_name="user_consents")
    op.drop_index("ix_user_consents_revoked_at", table_name="user_consents")
    op.drop_index("ix_user_consents_document_id", table_name="user_consents")
    op.drop_index("ix_user_consents_form_type", table_name="user_consents")
    op.drop_index("ix_user_consents_consent_type", table_name="user_consents")
    op.drop_index("ix_user_consents_user_id", table_name="user_consents")
    op.drop_table("user_consents")

    op.drop_index("uq_legal_documents_type_form_version", table_name="legal_documents")
    op.drop_index("ix_legal_documents_status", table_name="legal_documents")
    op.drop_index("ix_legal_documents_form_type", table_name="legal_documents")
    op.drop_index("ix_legal_documents_document_type", table_name="legal_documents")
    op.drop_table("legal_documents")
