"""github_repo circl_badge

Revision ID: 4936c2f74a3c
Revises: f3b9d1e4a726
Create Date: 2026-10-28 11:21:59.273910

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4936c2f74a3c'
down_revision = 'f3b9d1e4a726'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('github_repo', schema=None) as batch_op:
        batch_op.add_column(sa.Column('circl_badge', sa.Boolean(), nullable=True))


def downgrade():
    with op.batch_alter_table('github_repo', schema=None) as batch_op:
        batch_op.drop_column('circl_badge')
