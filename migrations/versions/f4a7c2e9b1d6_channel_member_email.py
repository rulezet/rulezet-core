"""Messages: email setting per conversation (only adds)

Revision ID: f4a7c2e9b1d6
Revises: e2b6d4f8a1c3
"""
from alembic import op
import sqlalchemy as sa

revision = 'f4a7c2e9b1d6'
down_revision = 'e2b6d4f8a1c3'
branch_labels = None
depends_on = None


def upgrade():
    # default (follow "Messages by email" in the preferences) | on (always email this conversation) | off (never)
    with op.batch_alter_table('channel_member') as batch:
        batch.add_column(sa.Column('email_mode', sa.String(8), nullable=False, server_default='default'))


def downgrade():
    with op.batch_alter_table('channel_member') as batch:
        batch.drop_column('email_mode')
