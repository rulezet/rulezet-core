"""workflow colour and icon (only adds)

Revision ID: d4a7c2e9f1b8
Revises: f2b8d4e6a1c3
"""
from alembic import op
import sqlalchemy as sa

revision = 'd4a7c2e9f1b8'
down_revision = 'f2b8d4e6a1c3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('admin_workflow', schema=None) as batch_op:
        batch_op.add_column(sa.Column('color', sa.String(length=7), nullable=True))
        batch_op.add_column(sa.Column('icon', sa.String(length=64), nullable=True))


def downgrade():
    with op.batch_alter_table('admin_workflow', schema=None) as batch_op:
        batch_op.drop_column('icon')
        batch_op.drop_column('color')
