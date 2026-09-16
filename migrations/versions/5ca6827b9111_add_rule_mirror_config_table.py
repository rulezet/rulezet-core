"""add rule_mirror_config table

Revision ID: 5ca6827b9111
Revises: abd5af3fd65a
Create Date: 2026-09-11 13:51:57.421051

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5ca6827b9111'
down_revision = 'abd5af3fd65a'
branch_labels = None
depends_on = None


def upgrade():
    # NOTE: autogenerate also proposed dropping the rule.*_trgm GIN indexes
    # from migrations e9b5cc35778e/abd5af3fd65a — a known false positive,
    # since those were created via raw op.execute() (CONCURRENTLY, not
    # representable as a plain SQLAlchemy Index()) and so aren't visible to
    # autogenerate's model diff. Deliberately removed from this migration.
    op.create_table('rule_mirror_config',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('repo_url', sa.String(length=512), nullable=True),
    sa.Column('github_token', sa.String(length=512), nullable=True),
    sa.Column('branch', sa.String(length=128), nullable=False),
    sa.Column('last_synced_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('updated_by_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['updated_by_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('rule_mirror_config')
