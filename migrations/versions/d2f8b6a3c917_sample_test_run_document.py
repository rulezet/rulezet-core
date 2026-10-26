"""sample_test_run: the tested document (a rule saved right after its test gets the result)

Revision ID: d2f8b6a3c917
Revises: c4e7a1f09d52
Create Date: 2026-10-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd2f8b6a3c917'
down_revision = 'c4e7a1f09d52'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('sample_test_run', schema=None) as batch_op:
        batch_op.add_column(sa.Column('document', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('sample_test_run', schema=None) as batch_op:
        batch_op.drop_column('document')
