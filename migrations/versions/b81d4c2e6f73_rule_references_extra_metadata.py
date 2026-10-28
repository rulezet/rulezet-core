"""rule: references and other metadata read from the rule's text

Revision ID: b81d4c2e6f73
Revises: a7c3e91d5b20
Create Date: 2026-10-26 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b81d4c2e6f73'
down_revision = 'a7c3e91d5b20'
branch_labels = None
depends_on = None


def upgrade():
    # nullable, no default: adding them does not rewrite the rule table; existing rules are
    # filled by the reparse_rule_metadata job (Admin → Bulk parse fields → References & metadata)
    with op.batch_alter_table('rule', schema=None) as batch_op:
        batch_op.add_column(sa.Column('rule_references', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('extra_metadata', sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table('rule', schema=None) as batch_op:
        batch_op.drop_column('extra_metadata')
        batch_op.drop_column('rule_references')
