"""add_score_weights_to_organizations

Revision ID: e7381992a101
Revises: bbd94ce37627
Create Date: 2026-08-27 20:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e7381992a101"
down_revision: Union[str, Sequence[str], None] = "bbd94ce37627"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("organizations", sa.Column("score_weights", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("organizations", "score_weights")
