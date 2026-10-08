"""add email_enabled to instance config

Revision ID: e5a1c7d9b3f2
Revises: d4f8b2c6e1a3
Create Date: 2026-09-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5a1c7d9b3f2'
down_revision = 'd4f8b2c6e1a3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('instance_config', schema=None) as batch_op:
        batch_op.add_column(sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    with op.batch_alter_table('instance_config', schema=None) as batch_op:
        batch_op.drop_column('email_enabled')
