"""rule: references added by hand (create / edit form)

Revision ID: c4e7a1f09d52
Revises: b81d4c2e6f73
Create Date: 2026-10-26 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4e7a1f09d52'
down_revision = 'b81d4c2e6f73'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('rule', schema=None) as batch_op:
        batch_op.add_column(sa.Column('manual_references', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('rule', schema=None) as batch_op:
        batch_op.drop_column('manual_references')
