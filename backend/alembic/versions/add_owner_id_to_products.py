"""add owner_id to products

Revision ID: add_owner_id_to_products
Revises: e8e176a9b093
Create Date: 2025-06-15 18:45:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'add_owner_id_to_products'
down_revision = 'e8e176a9b093'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1) add column only if it doesn't exist
    op.execute(
        "ALTER TABLE products ADD COLUMN IF NOT EXISTS owner_id INTEGER"
    )
    # 2) backfill from owner_email → users.id
    op.execute("""
        UPDATE products
        SET owner_id = u.id
        FROM users u
        WHERE products.owner_email = u.email
    """)
    # 3) enforce NOT NULL
    op.execute(
        "ALTER TABLE products ALTER COLUMN owner_id SET NOT NULL"
    )
    # 4) add FK constraint (will error if already exists, so drop first if needed)
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS fk_products_owner_id_users")
    op.execute("""
        ALTER TABLE products
        ADD CONSTRAINT fk_products_owner_id_users
        FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
    """)

def downgrade() -> None:
    op.execute("ALTER TABLE products DROP CONSTRAINT IF EXISTS fk_products_owner_id_users")
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS owner_id")
