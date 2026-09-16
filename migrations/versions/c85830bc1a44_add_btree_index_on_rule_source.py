"""add btree index on rule.source

Revision ID: c85830bc1a44
Revises: cfee08ac0eb5
Create Date: 2026-09-16 11:08:07.299994

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c85830bc1a44'
down_revision = 'cfee08ac0eb5'
branch_labels = None
depends_on = None


def upgrade():
    # The existing ix_rule_source_trgm (GIN, pg_trgm) is built for fuzzy
    # ILIKE/substring search — poor at exact-match/EXISTS lookups, which
    # the new GithubRepo incremental-sync write paths and the rewritten
    # GitHub Sources list (per-repo EXISTS filters against Rule.source)
    # now do frequently. A plain btree covers those efficiently.
    op.create_index('ix_rule_source_btree', 'rule', ['source'], unique=False)


def downgrade():
    op.drop_index('ix_rule_source_btree', table_name='rule')
