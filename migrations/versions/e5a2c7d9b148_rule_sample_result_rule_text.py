"""rule_sample_result: the rule as it was tested

Revision ID: e5a2c7d9b148
Revises: d2f8b6a3c917
Create Date: 2026-10-27 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5a2c7d9b148'
down_revision = 'd2f8b6a3c917'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('rule_sample_result', schema=None) as batch_op:
        batch_op.add_column(sa.Column('rule_text', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('rule_sample_result', schema=None) as batch_op:
        batch_op.drop_column('rule_text')
