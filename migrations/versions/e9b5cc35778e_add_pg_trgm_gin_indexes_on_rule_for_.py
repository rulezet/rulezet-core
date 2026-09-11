"""add pg_trgm GIN indexes on rule for fast substring search

Revision ID: e9b5cc35778e
Revises: 9d93dd41e316
Create Date: 2026-09-11 07:57:51.641151

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e9b5cc35778e'
down_revision = '9d93dd41e316'
branch_labels = None
depends_on = None


_TRGM_COLUMNS = ['title', 'description', 'author', 'to_string', 'uuid', 'original_uuid', 'format']


def upgrade():
    # filter_rules() (rule_core.py) searches these columns with leading-wildcard
    # ILIKE ('%term%') — a plain btree index can never serve that, forcing a
    # full sequential scan (+ per-row ILIKE) over the whole rule table on every
    # search. pg_trgm GIN indexes are what Postgres actually uses to accelerate
    # ILIKE/LIKE substring matching — no query-code change needed, the planner
    # picks them up automatically once they exist.
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')

    # CONCURRENTLY so building these on a live, large (~600k row) table never
    # blocks reads/writes against `rule` — this cannot run inside a
    # transaction block, hence autocommit_block().
    with op.get_context().autocommit_block():
        for col in _TRGM_COLUMNS:
            op.execute(
                f'CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rule_{col}_trgm '
                f'ON rule USING gin ({col} gin_trgm_ops)'
            )

    # Give the planner fresh stats right away rather than waiting on autovacuum.
    op.execute('ANALYZE rule')


def downgrade():
    with op.get_context().autocommit_block():
        for col in reversed(_TRGM_COLUMNS):
            op.execute(f'DROP INDEX CONCURRENTLY IF EXISTS ix_rule_{col}_trgm')
