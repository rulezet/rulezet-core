"""add format/license/cve/conflict aggregates to github_repo

Revision ID: 505365166a75
Revises: c85830bc1a44
Create Date: 2026-09-16 11:27:15.289923

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '505365166a75'
down_revision = 'c85830bc1a44'
branch_labels = None
depends_on = None


def upgrade():
    # NOTE: hand-edited — autogenerate also proposed dropping 9 unrelated
    # trigram/btree indexes on `rule` that exist in the DB but aren't
    # declared on the SQLAlchemy model (a pre-existing, known mismatch —
    # see migrations cfee08ac0eb5/c85830bc1a44). Stripped; only the
    # github_repo columns below are this migration's actual intent.
    with op.batch_alter_table('github_repo', schema=None) as batch_op:
        batch_op.add_column(sa.Column('format_counts', sa.JSON(), nullable=False, server_default='{}'))
        batch_op.add_column(sa.Column('license_counts', sa.JSON(), nullable=False, server_default='{}'))
        batch_op.add_column(sa.Column('cve_count', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('conflict_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    with op.batch_alter_table('github_repo', schema=None) as batch_op:
        batch_op.drop_column('conflict_count')
        batch_op.drop_column('cve_count')
        batch_op.drop_column('license_counts')
        batch_op.drop_column('format_counts')
