"""Add created_at to users (no-op after full baseline)

Revision ID: fc4dda015f56
Revises: fc8e33aeeef9
Create Date: 2025-05-22 20:53:03.631633

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'fc4dda015f56'
down_revision = 'fc8e33aeeef9'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # already handled by the new baseline schema
    pass

def downgrade() -> None:
    # baseline downgrade will drop this column
    pass