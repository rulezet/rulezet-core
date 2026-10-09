"""rule_scope: several declarations per user and rule (drop uq_rule_scope_user)

Exact duplicates are refused by the application (rule_core.save_scope).

Revision ID: b7d2e4f6a8c1
Revises: a4c8e1f2b9d3
Create Date: 2026-10-09 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7d2e4f6a8c1'
down_revision = 'a4c8e1f2b9d3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('rule_scope', schema=None) as batch_op:
        batch_op.drop_constraint('uq_rule_scope_user', type_='unique')
        batch_op.create_index(batch_op.f('ix_rule_scope_user_id'), ['user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('rule_scope', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_rule_scope_user_id'))
        batch_op.create_unique_constraint('uq_rule_scope_user', ['rule_id', 'user_id'])
