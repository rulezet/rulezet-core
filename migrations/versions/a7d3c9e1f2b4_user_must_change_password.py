"""user.must_change_password: the first admin changes the generated password on first login

Revision ID: a7d3c9e1f2b4
Revises: 4936c2f74a3c
Create Date: 2026-10-28
"""
from alembic import op
import sqlalchemy as sa

revision = 'a7d3c9e1f2b4'
down_revision = '4936c2f74a3c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('must_change_password')
