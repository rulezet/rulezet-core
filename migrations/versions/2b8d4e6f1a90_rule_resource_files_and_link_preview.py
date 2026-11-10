"""rule resource: uploaded text files and link previews

Revision ID: 2b8d4e6f1a90
Revises: 1567a80f1c2c
Create Date: 2026-11-10 12:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = '2b8d4e6f1a90'
down_revision = '1567a80f1c2c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('rule_resource', schema=None) as batch_op:
        batch_op.add_column(sa.Column('filename', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('size', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('preview', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('rule_resource', schema=None) as batch_op:
        batch_op.drop_column('preview')
        batch_op.drop_column('size')
        batch_op.drop_column('filename')
