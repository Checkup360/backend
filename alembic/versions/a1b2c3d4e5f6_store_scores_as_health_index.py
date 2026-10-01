"""rename score columns to health index names

Revision ID: a1b2c3d4e5f6
Revises: f7c8d9e0f1a2
Create Date: 2026-10-01 12:00:00.000000

Renames score columns so their names state the health index direction.
Values are converted in a follow-up change.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("risk_scores", "normalized_value", new_column_name="health_index")
    op.alter_column(
        "member_overall_scores",
        "overall_score",
        new_column_name="overall_health_index",
    )


def downgrade() -> None:
    op.alter_column(
        "member_overall_scores",
        "overall_health_index",
        new_column_name="overall_score",
    )
    op.alter_column("risk_scores", "health_index", new_column_name="normalized_value")
