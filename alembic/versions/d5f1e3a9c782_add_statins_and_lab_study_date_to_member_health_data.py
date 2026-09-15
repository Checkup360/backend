"""add statins and lab_study_date to member_health_data

Revision ID: d5f1e3a9c782
Revises: 0a5c2a2cb184
Create Date: 2026-09-15 20:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d5f1e3a9c782"
down_revision: Union[str, Sequence[str], None] = "0a5c2a2cb184"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "member_health_data",
        sa.Column("statins", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "member_health_data",
        sa.Column("lab_study_date", sa.String(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("member_health_data", "lab_study_date")
    op.drop_column("member_health_data", "statins")
