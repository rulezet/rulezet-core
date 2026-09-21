"""add pg_trgm GIN index on rule cve_id

Revision ID: aaa9fcaae28c
Revises: a091a3300f88
Create Date: 2026-09-21 13:48:18.289979

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aaa9fcaae28c'
down_revision = 'a091a3300f88'
branch_labels = None
depends_on = None


def upgrade():
    # search_rules_by_cve_patterns (rule_core.py, backing the public
    # search_rules_by_cve API — hit heavily by an external vulnerability-
    # lookup tool) matches Rule.cve_id with a leading-wildcard
    # ILIKE('%"CVE-..."%'). e9b5cc35778e already added pg_trgm GIN indexes
    # for the same reason on title/description/author/to_string/uuid/
    # original_uuid/format, but never on cve_id — this was the one column
    # still forcing a full sequential scan (+ per-row ILIKE) over the whole
    # rule table on every distinct CVE lookup, which is why several
    # concurrent calls for different CVEs could saturate disk I/O and slow
    # the whole site, not just this endpoint (confirmed via pg_stat_activity
    # showing multiple simultaneous DataFileRead waits on identical Rule
    # queries). No query-code change needed — the planner picks this up
    # automatically once it exists, same as the other trgm indexes.
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')

    # CONCURRENTLY so this never blocks reads/writes against `rule` while
    # building on a large live table — cannot run inside a transaction
    # block, hence autocommit_block(). Same pattern as e9b5cc35778e.
    with op.get_context().autocommit_block():
        op.execute(
            'CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_rule_cve_id_trgm '
            'ON rule USING gin (cve_id gin_trgm_ops)'
        )

    op.execute('ANALYZE rule')


def downgrade():
    with op.get_context().autocommit_block():
        op.execute('DROP INDEX CONCURRENTLY IF EXISTS ix_rule_cve_id_trgm')
