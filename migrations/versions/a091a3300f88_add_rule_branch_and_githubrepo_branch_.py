"""add Rule.branch and GithubRepo.branch_counts

Revision ID: a091a3300f88
Revises: 505365166a75
Create Date: 2026-09-18 13:28:43.839184

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a091a3300f88'
down_revision = '505365166a75'
branch_labels = None
depends_on = None


def upgrade():
    # NOTE: hand-trimmed after autogenerate — it also proposed dropping 9
    # pg_trgm GIN indexes + a btree index on `rule` (ix_rule_*_trgm,
    # ix_rule_source_btree). Those are real, load-bearing indexes added by
    # an earlier raw-SQL migration ("perf: add pg_trgm GIN indexes for fast
    # substring search") that autogenerate's model diff doesn't know about
    # (they're not declared as Column(index=True) in db.py), so it always
    # proposes removing them on any new autogenerate run. Only the two
    # actual new columns for this change are kept below.
    with op.batch_alter_table('github_repo', schema=None) as batch_op:
        # server_default so existing rows (there are many) get '{}' instead
        # of failing the NOT NULL constraint on ADD COLUMN.
        batch_op.add_column(sa.Column('branch_counts', sa.JSON(), nullable=False, server_default='{}'))

    with op.batch_alter_table('rule', schema=None) as batch_op:
        batch_op.add_column(sa.Column('branch', sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table('rule', schema=None) as batch_op:
        batch_op.drop_column('branch')

    with op.batch_alter_table('github_repo', schema=None) as batch_op:
        batch_op.drop_column('branch_counts')
