"""rename_member_biometrics_to_member_health_data

Revision ID: bbd94ce37627
Revises: f84a3c106d0e
Create Date: 2026-08-27 15:07:17.857028

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "bbd94ce37627"
down_revision: Union[str, Sequence[str], None] = "f84a3c106d0e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("member_biometrics", "member_health_data")


def downgrade() -> None:
    """Downgrade schema."""
    op.rename_table("member_health_data", "member_biometrics")
