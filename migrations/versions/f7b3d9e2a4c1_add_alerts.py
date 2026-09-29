"""add alerts (alert, alert_match, alert_sweep_state) and pref_alerts

Revision ID: f7b3d9e2a4c1
Revises: e5a1c7d9b3f2
Create Date: 2026-09-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f7b3d9e2a4c1'
down_revision = 'e5a1c7d9b3f2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'alert',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('targets', sa.JSON(), nullable=False),
        sa.Column('events', sa.JSON(), nullable=False),
        sa.Column('criteria', sa.JSON(), nullable=False),
        sa.Column('match_mode', sa.String(length=8), nullable=False, server_default='any'),
        sa.Column('notify_in_app', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('email_mode', sa.String(length=16), nullable=False, server_default='off'),
        sa.Column('match_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_triggered_at', sa.DateTime(), nullable=True),
        sa.Column('last_emailed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )
    op.create_index('ix_alert_uuid', 'alert', ['uuid'], unique=True)
    op.create_index('ix_alert_user_id', 'alert', ['user_id'])
    op.create_index('ix_alert_is_active', 'alert', ['is_active'])

    op.create_table(
        'alert_match',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('alert_id', sa.Integer(), sa.ForeignKey('alert.id', ondelete='CASCADE'), nullable=False),
        sa.Column('object_type', sa.String(length=16), nullable=False),
        sa.Column('object_id', sa.Integer(), nullable=False),
        sa.Column('object_version', sa.String(length=64), nullable=False, server_default=''),
        sa.Column('event', sa.String(length=16), nullable=False),
        sa.Column('matched_on', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('seen_at', sa.DateTime(), nullable=True),
        sa.Column('emailed_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('alert_id', 'object_type', 'object_id', 'event', 'object_version',
                            name='uq_alert_match'),
    )
    op.create_index('ix_alert_match_alert_id', 'alert_match', ['alert_id'])
    op.create_index('ix_alert_match_object_id', 'alert_match', ['object_id'])
    op.create_index('ix_alert_match_created_at', 'alert_match', ['created_at'])
    op.create_index('ix_alert_match_emailed_at', 'alert_match', ['emailed_at'])

    op.create_table(
        'alert_sweep_state',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('last_rule_id', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_bundle_id', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('rules_modified_at', sa.DateTime(), nullable=True),
        sa.Column('bundles_updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
    )

    with op.batch_alter_table('notification_preference', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pref_alerts', sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    with op.batch_alter_table('notification_preference', schema=None) as batch_op:
        batch_op.drop_column('pref_alerts')
    op.drop_table('alert_sweep_state')
    op.drop_index('ix_alert_match_emailed_at', table_name='alert_match')
    op.drop_index('ix_alert_match_created_at', table_name='alert_match')
    op.drop_index('ix_alert_match_object_id', table_name='alert_match')
    op.drop_index('ix_alert_match_alert_id', table_name='alert_match')
    op.drop_table('alert_match')
    op.drop_index('ix_alert_is_active', table_name='alert')
    op.drop_index('ix_alert_user_id', table_name='alert')
    op.drop_index('ix_alert_uuid', table_name='alert')
    op.drop_table('alert')
