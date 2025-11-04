"""Add initial whitelist user

Revision ID: a3973364bedd
Revises: 657eb80153db
Create Date: 2025-11-04 05:49:08.631037

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3973364bedd'
down_revision: Union[str, None] = '657eb80153db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add initial whitelist user (HH user ID: 174714255)."""
    # Use op.execute to insert data
    op.execute(
        """
        INSERT INTO allowed_users (hh_user_id, description, added_by, is_active, created_at, updated_at)
        VALUES (
            '174714255',
            'Initial whitelist user - system default',
            'system',
            true,
            NOW(),
            NOW()
        )
        ON CONFLICT (hh_user_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    """Remove initial whitelist user."""
    op.execute(
        """
        DELETE FROM allowed_users WHERE hh_user_id = '174714255' AND added_by = 'system';
        """
    )
