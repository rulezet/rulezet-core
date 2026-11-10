"""rule resource: PDF files (binary data)

Revision ID: 3c9e5f7a2b01
Revises: 2b8d4e6f1a90
Create Date: 2026-11-10 14:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = '3c9e5f7a2b01'
down_revision = '2b8d4e6f1a90'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('rule_resource', schema=None) as batch_op:
        batch_op.add_column(sa.Column('data', sa.LargeBinary(), nullable=True))


def downgrade():
    with op.batch_alter_table('rule_resource', schema=None) as batch_op:
        batch_op.drop_column('data')
