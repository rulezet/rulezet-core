"""workflows: retries, timeout, auto-pause after repeated failures, catch-up of a missed launch, several parents (all / any)

Only adds: columns with defaults (existing tasks behave exactly as before) and the
admin_task_dependency table (extra parents; the first parent stays in depends_on_schedule_id).

Revision ID: a9c4e2f7b3d1
Revises: f4c9d2a7e5b8
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa

revision = 'a9c4e2f7b3d1'
down_revision = 'f4c9d2a7e5b8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('admin_task_schedule', schema=None) as b:
        b.add_column(sa.Column('depends_on_mode', sa.String(length=10), nullable=False, server_default='all'))
        b.add_column(sa.Column('max_retries', sa.Integer(), nullable=False, server_default='0'))
        b.add_column(sa.Column('retry_delay_minutes', sa.Integer(), nullable=False, server_default='10'))
        b.add_column(sa.Column('timeout_minutes', sa.Integer(), nullable=True))
        b.add_column(sa.Column('max_consecutive_failures', sa.Integer(), nullable=False, server_default='0'))
        b.add_column(sa.Column('consecutive_failures', sa.Integer(), nullable=False, server_default='0'))
        b.add_column(sa.Column('auto_disabled_at', sa.DateTime(), nullable=True))
        b.add_column(sa.Column('catch_up', sa.Boolean(), nullable=False, server_default='false'))
        b.add_column(sa.Column('retry_at', sa.DateTime(), nullable=True))
    with op.batch_alter_table('admin_task_run', schema=None) as b:
        b.add_column(sa.Column('attempt', sa.Integer(), nullable=False, server_default='1'))
    op.create_table(
        'admin_task_dependency',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('schedule_id', sa.Integer(), sa.ForeignKey('admin_task_schedule.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('admin_task_schedule.id', ondelete='CASCADE'), nullable=False),
        sa.Column('condition', sa.String(length=20), nullable=False, server_default='success'),
        sa.UniqueConstraint('schedule_id', 'parent_id', name='uq_admin_task_dependency'),
    )
    op.create_index('ix_admin_task_dependency_schedule_id', 'admin_task_dependency', ['schedule_id'])
    op.create_index('ix_admin_task_dependency_parent_id', 'admin_task_dependency', ['parent_id'])


def downgrade():
    op.drop_index('ix_admin_task_dependency_parent_id', table_name='admin_task_dependency')
    op.drop_index('ix_admin_task_dependency_schedule_id', table_name='admin_task_dependency')
    op.drop_table('admin_task_dependency')
    with op.batch_alter_table('admin_task_run', schema=None) as b:
        b.drop_column('attempt')
    with op.batch_alter_table('admin_task_schedule', schema=None) as b:
        for col in ('retry_at', 'catch_up', 'auto_disabled_at', 'consecutive_failures', 'max_consecutive_failures',
                    'timeout_minutes', 'retry_delay_minutes', 'max_retries', 'depends_on_mode'):
            b.drop_column(col)
