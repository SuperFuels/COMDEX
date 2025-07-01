"""add supplier/buyer fields to users

Revision ID: c8b4d3db34d7
Revises: 5f40cc898654
Create Date: 2025-06-07 20:15:41.516138

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c8b4d3db34d7'
down_revision = '5f40cc898654'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema: add supplier/buyer fields and products table if needed."""
    # --- users table: add new columns ---
    op.add_column('users', sa.Column('business_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('address', sa.String(), nullable=True))
    op.add_column('users', sa.Column('delivery_address', sa.String(), nullable=True))
    op.add_column('users', sa.Column('products', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('monthly_spend', sa.String(), nullable=True))

    # --- products table: if it doesn’t already exist, create only the missing foreign-key link ---
    # (assuming your products table is already defined; if not, keep your existing create_table below)
    # Here, we only add the owner_email→users.email foreign key if not present:
    try:
        op.create_foreign_key(
            'fk_products_owner_email_users',
            'products', 'users',
            ['owner_email'], ['email'],
            ondelete='CASCADE'
        )
    except sa.exc.OperationalError:
        # foreign key already exists
        pass

    # (all your existing indexes on users are retained—no need to recreate)


def downgrade() -> None:
    """Downgrade schema: drop the columns added above."""
    # --- users: drop the supplier/buyer fields in reverse order ---
    op.drop_column('users', 'monthly_spend')
    op.drop_column('users', 'products')
    op.drop_column('users', 'delivery_address')
    op.drop_column('users', 'address')
    op.drop_column('users', 'business_name')
    
    # --- products: drop FK if desired ---
    with op.batch_alter_table('products') as batch_op:
        batch_op.drop_constraint('fk_products_owner_email_users', type_='foreignkey')