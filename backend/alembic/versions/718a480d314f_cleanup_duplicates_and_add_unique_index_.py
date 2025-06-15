"""cleanup duplicates and add unique index to products.title

Revision ID: 718a480d314f
Revises: 04e6930d6364
Create Date: 2025-06-16 00:XX:XX.XXXXXX
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = '718a480d314f'
down_revision = '04e6930d6364'
branch_labels = None
depends_on = None


def upgrade():
    # 1) Remove duplicate rows, keeping only the lowest-id per title
    op.execute("""
        DELETE FROM products
         WHERE id NOT IN (
               SELECT MIN(id) FROM products GROUP BY title
         );
    """)

    # 2) Create the unique index now that titles are unique
    op.create_index(
        op.f('ix_products_title'),
        'products',
        ['title'],
        unique=True
    )


def downgrade():
    # Drop the unique index if rolling back
    op.drop_index(op.f('ix_products_title'), table_name='products')