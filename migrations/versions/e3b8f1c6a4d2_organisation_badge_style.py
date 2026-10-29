"""organisation badge style: colour, icon and text, like a tag

Revision ID: e3b8f1c6a4d2
Revises: d7a2c4e9b1f3
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa

revision = 'e3b8f1c6a4d2'
down_revision = 'd7a2c4e9b1f3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('organisation', schema=None) as batch_op:
        batch_op.add_column(sa.Column('color', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('icon', sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column('label', sa.String(length=40), nullable=True))


def downgrade():
    with op.batch_alter_table('organisation', schema=None) as batch_op:
        batch_op.drop_column('label')
        batch_op.drop_column('icon')
        batch_op.drop_column('color')
