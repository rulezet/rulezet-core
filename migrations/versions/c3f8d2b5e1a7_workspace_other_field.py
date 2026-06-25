"""add workspace other field

Revision ID: c3f8d2b5e1a7
Revises: b2e7f4a1c9d3
Create Date: 2026-06-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = 'c3f8d2b5e1a7'
down_revision = 'b2e7f4a1c9d3'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    workspace_cols = {c['name'] for c in inspector.get_columns('workspace')}
    if 'other' not in workspace_cols:
        with op.batch_alter_table('workspace', schema=None) as batch_op:
            batch_op.add_column(sa.Column('other', sa.Text(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    workspace_cols = {c['name'] for c in inspector.get_columns('workspace')}
    if 'other' in workspace_cols:
        with op.batch_alter_table('workspace', schema=None) as batch_op:
            batch_op.drop_column('other')
