"""store scores as health index (higher is healthier)

Revision ID: a1b2c3d4e5f6
Revises: f7c8d9e0f1a2
Create Date: 2026-10-01 12:00:00.000000

Scores were persisted as risk values (0 = lowest risk, 100 = highest risk).
They are converted to a health index (0 = least healthy, 100 = healthiest)
and the columns are renamed so their direction is explicit. The conversion
``100 - value`` is its own inverse, so the downgrade applies it again.
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
    op.execute(
        "UPDATE risk_scores SET health_index = 100 - health_index "
        "WHERE health_index IS NOT NULL"
    )
    op.alter_column(
        "member_overall_scores",
        "overall_score",
        new_column_name="overall_health_index",
    )
    op.execute(
        "UPDATE member_overall_scores "
        "SET overall_health_index = 100 - overall_health_index"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE member_overall_scores "
        "SET overall_health_index = 100 - overall_health_index"
    )
    op.alter_column(
        "member_overall_scores",
        "overall_health_index",
        new_column_name="overall_score",
    )
    op.execute(
        "UPDATE risk_scores SET health_index = 100 - health_index "
        "WHERE health_index IS NOT NULL"
    )
    op.alter_column("risk_scores", "health_index", new_column_name="normalized_value")
