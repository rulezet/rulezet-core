"""Messages: channel automations (only adds)

Revision ID: a9e3d5c7f2b8
Revises: f4a7c2e9b1d6
"""
from alembic import op
import sqlalchemy as sa

revision = 'a9e3d5c7f2b8'
down_revision = 'f4a7c2e9b1d6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'channel_feed',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('channel_id', sa.Integer(), sa.ForeignKey('channel.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(24), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('user.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('posted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_posted_at', sa.DateTime(), nullable=True),
    )
    for col in ('channel_id', 'kind', 'target_id'):
        op.create_index(f'ix_channel_feed_{col}', 'channel_feed', [col])


def downgrade():
    op.drop_table('channel_feed')
