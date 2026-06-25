"""add remote_pull_log table

Revision ID: a3f1d2c9e5b7
Revises: 8b0b888f8d0d
Create Date: 2026-06-15 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = 'a3f1d2c9e5b7'
down_revision = '8b0b888f8d0d'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()
    if 'remote_pull_log' not in tables:
        op.create_table(
            'remote_pull_log',
            sa.Column('id',            sa.Integer(),     nullable=False),
            sa.Column('instance_uuid', sa.String(36),    nullable=True),
            sa.Column('instance_url',  sa.String(512),   nullable=True),
            sa.Column('ip_address',    sa.String(64),    nullable=True),
            sa.Column('rules_total',   sa.Integer(),     nullable=True),
            sa.Column('created_at',    sa.DateTime(),    nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index('ix_remote_pull_log_instance_uuid', 'remote_pull_log', ['instance_uuid'])
        op.create_index('ix_remote_pull_log_created_at',    'remote_pull_log', ['created_at'])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()
    if 'remote_pull_log' in tables:
        op.drop_index('ix_remote_pull_log_created_at',    table_name='remote_pull_log')
        op.drop_index('ix_remote_pull_log_instance_uuid', table_name='remote_pull_log')
        op.drop_table('remote_pull_log')
