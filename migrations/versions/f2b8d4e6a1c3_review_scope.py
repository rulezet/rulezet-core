"""a review can point to a scope its author declared on the rule (only adds a column)

Revision ID: f2b8d4e6a1c3
Revises: e1a7c3d5b9f2
"""
from alembic import op
import sqlalchemy as sa

revision = 'f2b8d4e6a1c3'
down_revision = 'e1a7c3d5b9f2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('rule_review') as batch:
        batch.add_column(sa.Column('scope_id', sa.Integer(), nullable=True))
        batch.create_foreign_key('fk_rule_review_scope_id', 'rule_scope', ['scope_id'], ['id'], ondelete='SET NULL')


def downgrade():
    with op.batch_alter_table('rule_review') as batch:
        batch.drop_constraint('fk_rule_review_scope_id', type_='foreignkey')
        batch.drop_column('scope_id')
