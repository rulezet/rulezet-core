"""add connection test tracking to rule_mirror_config

Revision ID: 3d53cf4fb0ba
Revises: a76fb80f2123
Create Date: 2026-09-11 14:48:10.968373

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3d53cf4fb0ba'
down_revision = 'a76fb80f2123'
branch_labels = None
depends_on = None


# NOTE: autogenerate also proposed dropping/recreating all 8 pg_trgm GIN
# indexes on `rule` — a known false positive (see 5ca6827b9111), since
# those were created via raw op.execute() and aren't visible to
# SQLAlchemy's model-based diffing. Stripped from this migration; do not
# reintroduce them.

def upgrade():
    with op.batch_alter_table('rule_mirror_config', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('last_error', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('last_tested_at', sa.DateTime(), nullable=True))
        batch_op.alter_column('is_verified', server_default=None)


def downgrade():
    with op.batch_alter_table('rule_mirror_config', schema=None) as batch_op:
        batch_op.drop_column('last_tested_at')
        batch_op.drop_column('last_error')
        batch_op.drop_column('is_verified')
