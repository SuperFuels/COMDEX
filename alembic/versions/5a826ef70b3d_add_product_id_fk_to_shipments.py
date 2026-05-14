"""add product_id FK to shipments

Revision ID: 5a826ef70b3d
Revises: 
Create Date: 2025-06-14 21:09:55.582701

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5a826ef70b3d'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # add product_id column
    op.add_column(
        'shipments',
        sa.Column('product_id', sa.Integer(), nullable=True, index=True)
    )
    # create FK constraint
    op.create_foreign_key(
        'fk_shipments_product',    # constraint name
        'shipments',               # source table
        'products',                # referent table
        ['product_id'],            # local cols
        ['id'],                    # remote cols
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # drop FK constraint first
    op.drop_constraint('fk_shipments_product', 'shipments', type_='foreignkey')
    # then drop the column
    op.drop_column('shipments', 'product_id')