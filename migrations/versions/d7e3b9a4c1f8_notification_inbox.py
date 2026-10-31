"""notifications as an inbox: starred, archived, labels; muted types and auto-archive in the
preferences (only adds)

Revision ID: d7e3b9a4c1f8
Revises: c4f1a8e2b7d6
"""
from alembic import op
import sqlalchemy as sa

revision = 'd7e3b9a4c1f8'
down_revision = 'c4f1a8e2b7d6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('notification', schema=None) as b:
        b.add_column(sa.Column('is_starred', sa.Boolean(), nullable=False, server_default=sa.false()))
        b.add_column(sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.false()))
        b.create_index('ix_notification_is_starred', ['is_starred'])
        b.create_index('ix_notification_is_archived', ['is_archived'])
    with op.batch_alter_table('notification_preference', schema=None) as b:
        b.add_column(sa.Column('muted_types', sa.Text(), nullable=True))
        b.add_column(sa.Column('auto_archive_days', sa.Integer(), nullable=False, server_default='0'))
    op.create_table(
        'notification_label',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=40), nullable=False),
        sa.Column('color', sa.String(length=7), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('user_id', 'name', name='uq_notification_label_user_name'),
    )
    op.create_index('ix_notification_label_user_id', 'notification_label', ['user_id'])
    op.create_table(
        'notification_label_link',
        sa.Column('notification_id', sa.Integer(), sa.ForeignKey('notification.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('label_id', sa.Integer(), sa.ForeignKey('notification_label.id', ondelete='CASCADE'), primary_key=True),
    )


def downgrade():
    op.drop_table('notification_label_link')
    op.drop_index('ix_notification_label_user_id', table_name='notification_label')
    op.drop_table('notification_label')
    with op.batch_alter_table('notification_preference', schema=None) as b:
        b.drop_column('auto_archive_days')
        b.drop_column('muted_types')
    with op.batch_alter_table('notification', schema=None) as b:
        b.drop_index('ix_notification_is_archived')
        b.drop_index('ix_notification_is_starred')
        b.drop_column('is_archived')
        b.drop_column('is_starred')
