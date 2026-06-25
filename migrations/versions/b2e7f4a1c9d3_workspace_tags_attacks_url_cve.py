"""add workspace tags, attacks, url, cve

Revision ID: b2e7f4a1c9d3
Revises: a9f3c1d2e8b5
Create Date: 2026-06-25
"""
from alembic import op
import sqlalchemy as sa

revision = 'b2e7f4a1c9d3'
down_revision = 'a9f3c1d2e8b5'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('workspace', sa.Column('url', sa.Text(), nullable=True))
    op.add_column('workspace', sa.Column('cve_id', sa.Text(), nullable=True))

    op.create_table(
        'workspace_tag_association',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('workspace.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tag_id', sa.Integer(), sa.ForeignKey('tag.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('workspace_id', 'tag_id', name='uq_ws_tag'),
    )

    op.create_table(
        'workspace_attack_association',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('workspace_id', sa.Integer(), sa.ForeignKey('workspace.id', ondelete='CASCADE'), nullable=False),
        sa.Column('technique_id', sa.String(20), sa.ForeignKey('attack_technique.technique_id', ondelete='CASCADE'), nullable=False),
        sa.UniqueConstraint('workspace_id', 'technique_id', name='uq_ws_attack'),
    )


def downgrade():
    op.drop_table('workspace_attack_association')
    op.drop_table('workspace_tag_association')
    op.drop_column('workspace', 'cve_id')
    op.drop_column('workspace', 'url')
