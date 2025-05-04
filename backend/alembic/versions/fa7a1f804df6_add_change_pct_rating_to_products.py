"""add change_pct & rating to products

Revision ID: fa7a1f804df6
Revises: aa5d58481454
Create Date: 2025-05-04 10:16:36.569338

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fa7a1f804df6'
down_revision = 'aa5d58481454'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # add change_pct and rating, set existing rows to 0.0
    op.add_column(
        'products',
        sa.Column('change_pct', sa.Float(), nullable=False, server_default='0')
    )
    op.add_column(
        'products',
        sa.Column('rating', sa.Float(), nullable=False, server_default='0')
    )
    # drop the server_default so new inserts must explicitly set or use your model default
    op.alter_column('products', 'change_pct', server_default=None)
    op.alter_column('products', 'rating',   server_default=None)


def downgrade() -> None:
    op.drop_column('products', 'rating')
    op.drop_column('products', 'change_pct')

