"""add risk_thresholds to organizations and score_weights

Revision ID: a2b3c4d5e6f7
Revises: f7c8d9e0f1a2
Create Date: 2026-10-04 11:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("risk_thresholds", sa.JSON(), nullable=True),
    )
    op.add_column(
        "organization_score_weights",
        sa.Column("risk_thresholds", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organization_score_weights", "risk_thresholds")
    op.drop_column("organizations", "risk_thresholds")
