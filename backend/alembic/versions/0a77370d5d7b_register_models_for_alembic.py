"""register models for alembic

Revision ID: 0a77370d5d7b
Revises: fa7a1f804df6
Create Date: 2025-05-04 10:xx:xx.xxxxxx

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '0a77370d5d7b'
down_revision = 'fa7a1f804df6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # no-op: models are already in sync
    pass


def downgrade() -> None:
    # nothing to undo
    pass

