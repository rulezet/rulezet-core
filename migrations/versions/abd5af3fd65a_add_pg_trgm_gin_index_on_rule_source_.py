"""add pg_trgm GIN index on rule.source for github list perf

Revision ID: abd5af3fd65a
Revises: e9b5cc35778e
Create Date: 2026-09-11 09:25:56.258971

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'abd5af3fd65a'
down_revision = 'e9b5cc35778e'
branch_labels = None
depends_on = None


def upgrade():
    # get_optimized_github_data() (the /rule/github/list_github_url page)
    # filters Rule.source with a regex (github_pattern) and ILIKE substring
    # search — pg_trgm's GIN opclass accelerates both operators, same as the
    # earlier rule-search indexes. CONCURRENTLY so it never locks `rule`.
    with op.get_context().autocommit_block():
        op.execute(
            'CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rule_source_trgm '
            'ON rule USING gin (source gin_trgm_ops)'
        )
    op.execute('ANALYZE rule')


def downgrade():
    with op.get_context().autocommit_block():
        op.execute('DROP INDEX CONCURRENTLY IF EXISTS ix_rule_source_trgm')
