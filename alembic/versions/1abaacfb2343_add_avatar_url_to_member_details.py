"""add_avatar_url_to_member_details

Revision ID: 1abaacfb2343
Revises: 9c4f1e8b2d07
Create Date: 2026-08-31 17:00:12.487606

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "1abaacfb2343"
down_revision: Union[str, Sequence[str], None] = "9c4f1e8b2d07"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
