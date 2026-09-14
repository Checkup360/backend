"""clear base64 avatars

Revision ID: a7245aa9d706
Revises: 037ef28cd04b
Create Date: 2026-09-14 16:45:32.518490

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7245aa9d706"
down_revision: Union[str, Sequence[str], None] = "037ef28cd04b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        sa.text(
            "UPDATE member_details SET avatar_url = NULL WHERE avatar_url LIKE 'data:%'"
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
