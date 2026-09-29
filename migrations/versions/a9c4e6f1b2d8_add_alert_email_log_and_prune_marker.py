"""add alert_email_log and alert_sweep_state.last_pruned_at (alert anti-spam quotas)

Revision ID: a9c4e6f1b2d8
Revises: f7b3d9e2a4c1
Create Date: 2026-09-29 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a9c4e6f1b2d8'
down_revision = 'f7b3d9e2a4c1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'alert_email_log',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=False),
        sa.Column('alert_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('match_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.create_index('ix_alert_email_log_user_id', 'alert_email_log', ['user_id'])
    op.create_index('ix_alert_email_log_sent_at', 'alert_email_log', ['sent_at'])
    with op.batch_alter_table('alert_sweep_state', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_pruned_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('alert_sweep_state', schema=None) as batch_op:
        batch_op.drop_column('last_pruned_at')
    op.drop_index('ix_alert_email_log_sent_at', table_name='alert_email_log')
    op.drop_index('ix_alert_email_log_user_id', table_name='alert_email_log')
    op.drop_table('alert_email_log')
