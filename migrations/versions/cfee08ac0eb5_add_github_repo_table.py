"""add github_repo table

Revision ID: cfee08ac0eb5
Revises: 19a3cbae6794
Create Date: 2026-09-16 11:07:18.797961

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cfee08ac0eb5'
down_revision = '19a3cbae6794'
branch_labels = None
depends_on = None


def upgrade():
    # Autogenerate also wanted to DROP 8 unrelated trigram GIN indexes on
    # `rule` (ix_rule_*_trgm) — those exist in the real DB but aren't
    # declared on the SQLAlchemy models, so autogenerate's diff sees them
    # as "extra" and proposes removing them. They're real, load-bearing
    # search indexes (ILIKE/search performance across the app) — stripped
    # out here by hand, this migration only touches github_repo.
    op.create_table('github_repo',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('uuid', sa.String(length=36), nullable=False),
    sa.Column('url', sa.String(length=500), nullable=False),
    sa.Column('author', sa.String(length=255), nullable=True),
    sa.Column('rule_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('last_synced_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('github_repo', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_github_repo_author'), ['author'], unique=False)
        batch_op.create_index(batch_op.f('ix_github_repo_url'), ['url'], unique=True)
        batch_op.create_index(batch_op.f('ix_github_repo_uuid'), ['uuid'], unique=True)


def downgrade():
    with op.batch_alter_table('github_repo', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_github_repo_uuid'))
        batch_op.drop_index(batch_op.f('ix_github_repo_url'))
        batch_op.drop_index(batch_op.f('ix_github_repo_author'))

    op.drop_table('github_repo')
