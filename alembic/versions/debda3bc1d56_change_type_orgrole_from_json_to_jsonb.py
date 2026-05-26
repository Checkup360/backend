"""change type OrgRole from JSON to JSONB

Revision ID: debda3bc1d56
Revises: a42f64800437
Create Date: 2026-05-26 14:23:18.067365
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "debda3bc1d56"
down_revision: Union[str, Sequence[str], None] = "a42f64800437"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "memberships",
        "roles",
        existing_type=postgresql.JSON(),
        type_=postgresql.JSONB(),
        postgresql_using="roles::jsonb",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "memberships",
        "roles",
        existing_type=postgresql.JSONB(),
        type_=postgresql.JSON(),
        postgresql_using="roles::json",
        existing_nullable=False,
    )
