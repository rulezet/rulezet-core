"""rule.platforms: platforms named in a rule's metadata ("|Windows|Windows:Sysmon|"), for the rules list

Revision ID: b8e4d0f2a6c1
Revises: a7d3c9e1f2b4
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa

revision = 'b8e4d0f2a6c1'
down_revision = 'a7d3c9e1f2b4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('rule', schema=None) as batch_op:
        batch_op.add_column(sa.Column('platforms', sa.String(length=500), nullable=True))
        batch_op.create_index('ix_rule_platforms', ['platforms'], unique=False)


def downgrade():
    with op.batch_alter_table('rule', schema=None) as batch_op:
        batch_op.drop_index('ix_rule_platforms')
        batch_op.drop_column('platforms')
