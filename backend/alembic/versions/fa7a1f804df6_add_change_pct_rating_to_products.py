"""add change_pct & rating to products

Revision ID: fa7a1f804df6
Revises: aa5d58481454
Create Date: 2025-05-04 10:16:36.569338
"""
from alembic import op, context
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'fa7a1f804df6'
down_revision = 'aa5d58481454'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) add change_pct & rating with a server_default so existing rows get 0
    op.add_column(
        'products',
        sa.Column('change_pct', sa.Float(), nullable=False, server_default='0'),
    )
    op.add_column(
        'products',
        sa.Column('rating', sa.Float(), nullable=False, server_default='0'),
    )

    # 2) drop those defaults on DBs that support ALTER
    bind = op.get_bind()
    if bind.dialect.name != 'sqlite':
        op.alter_column('products', 'change_pct', server_default=None)
        op.alter_column('products', 'rating',     server_default=None)


def downgrade() -> None:
    op.drop_column('products', 'rating')
    op.drop_column('products', 'change_pct')