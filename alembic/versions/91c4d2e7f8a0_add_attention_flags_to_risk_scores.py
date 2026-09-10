"""add explicit attention flags to risk scores

Revision ID: 91c4d2e7f8a0
Revises: 8f3c1a7e2b14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "91c4d2e7f8a0"
down_revision: Union[str, Sequence[str], None] = "8f3c1a7e2b14"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "risk_scores",
        sa.Column("attention_flags", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("risk_scores", "attention_flags")
