"""drop superadmin removal requests (quorum removed)

Revision ID: 4e8f2d8760dd
Revises: a2b3c4d5e6f7
Create Date: 2026-10-04 12:00:00.000000

Superadmin removal no longer goes through a quorum vote: a superadmin removes
another directly while at least one remains, and the change is recorded in the
audit log. Past removal requests and votes are discarded on purpose. The
downgrade recreates both tables with their original schema, empty.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "4e8f2d8760dd"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("superadmin_removal_votes")
    op.drop_table("superadmin_removal_requests")


def downgrade() -> None:
    _create_removal_requests_table()
    _create_removal_votes_table()


def _create_removal_requests_table() -> None:
    op.create_table(
        "superadmin_removal_requests",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "requester_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="pending"
        ),
        sa.Column("required_votes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    for name, column in [
        ("ix_superadmin_removal_requests_org_id", "organization_id"),
        ("ix_superadmin_removal_requests_target_id", "target_user_id"),
        ("ix_superadmin_removal_requests_requester_id", "requester_user_id"),
        ("ix_superadmin_removal_requests_status", "status"),
    ]:
        op.create_index(name, "superadmin_removal_requests", [column])


def _create_removal_votes_table() -> None:
    op.create_table(
        "superadmin_removal_votes",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column(
            "request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("superadmin_removal_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "voter_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column(
            "voted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "request_id",
            "voter_user_id",
            name="uq_superadmin_removal_votes_request_voter",
        ),
    )
    op.create_index(
        "ix_superadmin_removal_votes_request_id",
        "superadmin_removal_votes",
        ["request_id"],
    )
    op.create_index(
        "ix_superadmin_removal_votes_voter_id",
        "superadmin_removal_votes",
        ["voter_user_id"],
    )
