"""add total_cholesterol and smoker to member_health_data

Revision ID: 037ef28cd04b
Revises: 6075406f6271
Create Date: 2026-09-14 13:00:37.530190

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "037ef28cd04b"
down_revision: Union[str, Sequence[str], None] = "6075406f6271"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "member_health_data",
        sa.Column("total_cholesterol", sa.Float(), nullable=True),
    )
    op.add_column(
        "member_health_data",
        sa.Column("smoker", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("member_health_data", "smoker")
    op.drop_column("member_health_data", "total_cholesterol")
