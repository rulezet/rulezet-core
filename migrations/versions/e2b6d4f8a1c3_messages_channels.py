"""Messages: channels, members, messages, reactions; messages by email preference (only adds)

Revision ID: e2b6d4f8a1c3
Revises: d7e3b9a4c1f8
"""
from alembic import op
import sqlalchemy as sa

revision = 'e2b6d4f8a1c3'
down_revision = 'd7e3b9a4c1f8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'channel',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(36), nullable=False),
        sa.Column('kind', sa.String(16), nullable=False),
        sa.Column('name', sa.String(80), nullable=True),
        sa.Column('topic', sa.String(300), nullable=True),
        sa.Column('is_private', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('ref_type', sa.String(20), nullable=True),
        sa.Column('ref_key', sa.String(120), nullable=True),
        sa.Column('ref_label', sa.String(255), nullable=True),
        sa.Column('avatar', sa.String(80), nullable=True),
        sa.Column('invite_code', sa.String(40), nullable=True),
        sa.Column('members_can_invite', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('user.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_message_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_channel_uuid', 'channel', ['uuid'], unique=True)
    op.create_index('ix_channel_invite_code', 'channel', ['invite_code'], unique=True)
    for col in ('kind', 'is_private', 'ref_type', 'ref_key', 'last_message_at'):
        op.create_index(f'ix_channel_{col}', 'channel', [col])

    op.create_table(
        'channel_member',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('channel_id', sa.Integer(), sa.ForeignKey('channel.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(16), nullable=False),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.Column('last_read_id', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_muted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_starred', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('cleared_id', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('emailed_id', sa.Integer(), nullable=False, server_default='0'),
        sa.UniqueConstraint('channel_id', 'user_id', name='uq_channel_member'),
    )
    op.create_index('ix_channel_member_channel_id', 'channel_member', ['channel_id'])
    op.create_index('ix_channel_member_user_id', 'channel_member', ['user_id'])

    op.create_table(
        'channel_message',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(36), nullable=False),
        sa.Column('channel_id', sa.Integer(), sa.ForeignKey('channel.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='SET NULL'), nullable=True),
        sa.Column('kind', sa.String(16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('reply_to_id', sa.Integer(), sa.ForeignKey('channel_message.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('edited_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_channel_message_uuid', 'channel_message', ['uuid'], unique=True)
    for col in ('channel_id', 'user_id', 'created_at'):
        op.create_index(f'ix_channel_message_{col}', 'channel_message', [col])

    op.create_table(
        'channel_reaction',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('message_id', sa.Integer(), sa.ForeignKey('channel_message.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('emoji', sa.String(16), nullable=False),
        sa.UniqueConstraint('message_id', 'user_id', 'emoji', name='uq_channel_reaction'),
    )
    op.create_index('ix_channel_reaction_message_id', 'channel_reaction', ['message_id'])

    # Messages by email: off | direct (direct messages and mentions) | all
    with op.batch_alter_table('notification_preference') as batch:
        batch.add_column(sa.Column('email_messages', sa.String(16), nullable=False, server_default='off'))


def downgrade():
    with op.batch_alter_table('notification_preference') as batch:
        batch.drop_column('email_messages')
    op.drop_table('channel_reaction')
    op.drop_table('channel_message')
    op.drop_table('channel_member')
    op.drop_table('channel')
