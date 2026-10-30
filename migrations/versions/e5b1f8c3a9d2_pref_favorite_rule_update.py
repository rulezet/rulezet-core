"""notification preference: favorite rule updated (only adds)

Revision ID: e5b1f8c3a9d2
Revises: d4a7c2e9f1b8
"""
from alembic import op
import sqlalchemy as sa

revision = 'e5b1f8c3a9d2'
down_revision = 'd4a7c2e9f1b8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('notification_preference', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pref_favorite_rule_update', sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    with op.batch_alter_table('notification_preference', schema=None) as batch_op:
        batch_op.drop_column('pref_favorite_rule_update')
