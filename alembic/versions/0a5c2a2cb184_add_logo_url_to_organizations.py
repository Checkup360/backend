"""add logo_url to organizations

Revision ID: 0a5c2a2cb184
Revises: a7245aa9d706
Create Date: 2026-09-14 20:51:53.582964

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0a5c2a2cb184"
down_revision: Union[str, Sequence[str], None] = "a7245aa9d706"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("organizations", sa.Column("logo_url", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("organizations", "logo_url")
