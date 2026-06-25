"""add workspace tags, attacks, url, cve

Revision ID: b2e7f4a1c9d3
Revises: a9f3c1d2e8b5
Create Date: 2026-06-25
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = 'b2e7f4a1c9d3'
down_revision = 'a9f3c1d2e8b5'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    workspace_cols = {c['name'] for c in inspector.get_columns('workspace')}
    if 'url' not in workspace_cols:
        with op.batch_alter_table('workspace', schema=None) as batch_op:
            batch_op.add_column(sa.Column('url', sa.Text(), nullable=True))
            batch_op.add_column(sa.Column('cve_id', sa.Text(), nullable=True))

    tables = inspector.get_table_names()
    if 'workspace_tag_association' not in tables:
        op.create_table(
            'workspace_tag_association',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('workspace.id', ondelete='CASCADE'), nullable=False),
            sa.Column('tag_id', sa.Integer(), sa.ForeignKey('tag.id', ondelete='CASCADE'), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.UniqueConstraint('workspace_id', 'tag_id', name='uq_ws_tag'),
        )

    if 'workspace_attack_association' not in tables:
        op.create_table(
            'workspace_attack_association',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('workspace.id', ondelete='CASCADE'), nullable=False),
            sa.Column('technique_id', sa.String(20), sa.ForeignKey('attack_technique.technique_id', ondelete='CASCADE'), nullable=False),
            sa.UniqueConstraint('workspace_id', 'technique_id', name='uq_ws_attack'),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = inspector.get_table_names()
    if 'workspace_attack_association' in tables:
        op.drop_table('workspace_attack_association')
    if 'workspace_tag_association' in tables:
        op.drop_table('workspace_tag_association')

    workspace_cols = {c['name'] for c in inspector.get_columns('workspace')}
    with op.batch_alter_table('workspace', schema=None) as batch_op:
        if 'cve_id' in workspace_cols:
            batch_op.drop_column('cve_id')
        if 'url' in workspace_cols:
            batch_op.drop_column('url')
