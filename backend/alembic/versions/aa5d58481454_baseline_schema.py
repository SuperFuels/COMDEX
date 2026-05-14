"""baseline schema

Revision ID: aa5d58481454
Revises: 
Create Date: 2025-05-04 10:09:42.631547
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aa5d58481454'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── users ────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('email', sa.String, nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String, nullable=False),
        sa.Column('wallet_address', sa.String, nullable=True, unique=True, index=True),
        sa.Column('role', sa.String, nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ─── products ───────────────────────────────────────────────────────────
    op.create_table(
        'products',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('description', sa.String, nullable=True),
        sa.Column('price', sa.Float, nullable=False),
        sa.Column('owner_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ─── deals ────────────────────────────────────────────────────────────────
    op.create_table(
        'deals',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('product_id', sa.Integer, sa.ForeignKey('products.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('buyer_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('supplier_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('price', sa.Float, nullable=False),
        sa.Column('status', sa.String, nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ─── contracts ───────────────────────────────────────────────────────────
    op.create_table(
        'contracts',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('deal_id', sa.Integer, sa.ForeignKey('deals.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('terms', sa.String, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('contracts')
    op.drop_table('deals')
    op.drop_table('products')
    op.drop_table('users')