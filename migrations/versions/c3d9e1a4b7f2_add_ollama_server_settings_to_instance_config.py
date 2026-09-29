"""add ollama server settings to instance config

Revision ID: c3d9e1a4b7f2
Revises: aaa9fcaae28c
Create Date: 2026-09-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d9e1a4b7f2'
down_revision = 'aaa9fcaae28c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('instance_config', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ollama_url', sa.String(length=512), nullable=True))
        batch_op.add_column(sa.Column('ollama_default_model', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('ollama_remote_allowed', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table('instance_config', schema=None) as batch_op:
        batch_op.drop_column('ollama_remote_allowed')
        batch_op.drop_column('ollama_default_model')
        batch_op.drop_column('ollama_url')
