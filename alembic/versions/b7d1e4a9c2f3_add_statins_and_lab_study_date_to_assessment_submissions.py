"""add statins and lab_study_date to assessment_submissions

Revision ID: b7d1e4a9c2f3
Revises: 4e8f2d8760dd
Create Date: 2026-10-22 10:00:00.000000

The metabolic form submits statins and lab_study_date, but submission
snapshots had nowhere to store them.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b7d1e4a9c2f3"
down_revision: Union[str, Sequence[str], None] = "4e8f2d8760dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "assessment_submissions", sa.Column("statins", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "assessment_submissions",
        sa.Column("lab_study_date", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assessment_submissions", "lab_study_date")
    op.drop_column("assessment_submissions", "statins")
