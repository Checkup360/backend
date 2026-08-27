"""add_clinical_columns_to_member_biometrics

Revision ID: f84a3c106d0e
Revises: 6f5682b0ab16
Create Date: 2026-08-27 14:32:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f84a3c106d0e"
down_revision: Union[str, Sequence[str], None] = "6f5682b0ab16"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "member_biometrics", sa.Column("snoring", sa.Boolean(), nullable=True)
    )
    op.add_column("member_biometrics", sa.Column("tired", sa.Boolean(), nullable=True))
    op.add_column(
        "member_biometrics", sa.Column("observed_apnea", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "member_biometrics",
        sa.Column("hypertension_medication", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "member_biometrics",
        sa.Column("daily_physical_activity", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "member_biometrics", sa.Column("fruits_vegetables", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "member_biometrics",
        sa.Column("previous_high_glucose", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "member_biometrics", sa.Column("family_diabetes", sa.String(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("member_biometrics", "family_diabetes")
    op.drop_column("member_biometrics", "previous_high_glucose")
    op.drop_column("member_biometrics", "fruits_vegetables")
    op.drop_column("member_biometrics", "daily_physical_activity")
    op.drop_column("member_biometrics", "hypertension_medication")
    op.drop_column("member_biometrics", "observed_apnea")
    op.drop_column("member_biometrics", "tired")
    op.drop_column("member_biometrics", "snoring")
