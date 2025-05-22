"""Add created_at to users

Revision ID: fc4dda015f56
Revises: fc8e33aeeef9
Create Date: 2025-05-22 20:53:03.631633

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc4dda015f56'
down_revision: Union[str, None] = 'fc8e33aeeef9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1) Add the column with a server_default so existing rows get a timestamp
    op.add_column(
        'users',
        sa.Column(
            'created_at',
            sa.DateTime(),
            server_default=sa.func.now(),
            nullable=False,
        )
    )
    # 2) Drop the default now that all rows have a value
    op.alter_column('users', 'created_at', server_default=None)

    # 3) Remove the old index
    op.drop_index('ix_users_name', table_name='users')


def downgrade() -> None:
    """Downgrade schema."""
    # recreate index
    op.create_index('ix_users_name', 'users', ['name'], unique=False)
    # drop the column
    op.drop_column('users', 'created_at')
