"""merge products-owner and users branches

Revision ID: 178ee1ed534e
Revises: e8e176a9b093, add_owner_id_to_products
Create Date: 2025-06-15 18:45:57.641320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '178ee1ed534e'
down_revision: Union[str, None] = ('e8e176a9b093', 'add_owner_id_to_products')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
