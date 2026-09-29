"""add audit_logs table

Revision ID: f6b7c8d9e0f1
Revises: e5a6c7d8e9f0
Create Date: 2026-09-29 11:35:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f6b7c8d9e0f1"
down_revision: Union[str, Sequence[str], None] = "e5a6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_audit_logs_user_id",
        "audit_logs",
        ["user_id"],
    )
    op.create_index(
        "ix_audit_logs_organization_id",
        "audit_logs",
        ["organization_id"],
    )
    op.create_index(
        "ix_audit_logs_action",
        "audit_logs",
        ["action"],
    )
    op.create_index(
        "ix_audit_logs_resource_type",
        "audit_logs",
        ["resource_type"],
    )
    op.create_index(
        "ix_audit_logs_resource_id",
        "audit_logs",
        ["resource_id"],
    )
    op.create_index(
        "ix_audit_logs_created_at",
        "audit_logs",
        ["created_at"],
    )
    op.create_index(
        "ix_audit_logs_user_created_at",
        "audit_logs",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_audit_logs_org_created_at",
        "audit_logs",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "ix_audit_logs_action_created_at",
        "audit_logs",
        ["action", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_action_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_org_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_resource_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_resource_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_organization_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")
