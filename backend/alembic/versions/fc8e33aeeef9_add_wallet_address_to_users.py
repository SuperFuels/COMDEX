"""add wallet_address to users

Revision ID: fc8e33aeeef9
Revises: 0a77370d5d7b
Create Date: 2025-05-07 16:56:43.500558

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc8e33aeeef9'
down_revision: Union[str, None] = '0a77370d5d7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
