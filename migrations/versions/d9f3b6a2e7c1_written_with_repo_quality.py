"""how a rule was written (human / AI / both), quality score of git sources (only adds columns)

Revision ID: d9f3b6a2e7c1
Revises: c8e2a5f1d9b4
"""
from alembic import op
import sqlalchemy as sa

revision = 'd9f3b6a2e7c1'
down_revision = 'c8e2a5f1d9b4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('rule') as batch:
        batch.add_column(sa.Column('written_with', sa.String(16), nullable=True))
    with op.batch_alter_table('github_repo') as batch:
        batch.add_column(sa.Column('quality_score', sa.Float(), nullable=True))
        batch.add_column(sa.Column('quality_breakdown', sa.JSON(), nullable=True))
        batch.add_column(sa.Column('quality_computed_at', sa.DateTime(), nullable=True))
        batch.create_index('ix_github_repo_quality_score', ['quality_score'])


def downgrade():
    with op.batch_alter_table('github_repo') as batch:
        batch.drop_index('ix_github_repo_quality_score')
        batch.drop_column('quality_computed_at')
        batch.drop_column('quality_breakdown')
        batch.drop_column('quality_score')
    with op.batch_alter_table('rule') as batch:
        batch.drop_column('written_with')
