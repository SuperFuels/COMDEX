"""Add business_name, address, delivery_address, products, monthly_spend to users

Revision ID: a54affaa2a8e
Revises: fc4dda015f56
Create Date: 2025-05-29 18:24:30.341327
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a54affaa2a8e'
down_revision = 'fc4dda015f56'
branch_labels = None
depends_on = None

def upgrade() -> None:
    """Upgrade schema by adding new supplier/buyer fields to users."""
    op.add_column('users', sa.Column('business_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('address', sa.String(), nullable=True))
    op.add_column('users', sa.Column('delivery_address', sa.String(), nullable=True))
    op.add_column('users', sa.Column('products', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('monthly_spend', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema by removing supplier/buyer fields from users."""
    op.drop_column('users', 'monthly_spend')
    op.drop_column('users', 'products')
    op.drop_column('users', 'delivery_address')
    op.drop_column('users', 'address')
    op.drop_column('users', 'business_name')
