"""a review carries a 1-5 rating and how the reviewer sees the rule written (only adds columns)

Revision ID: e1a7c3d5b9f2
Revises: d9f3b6a2e7c1
"""
from alembic import op
import sqlalchemy as sa

revision = 'e1a7c3d5b9f2'
down_revision = 'd9f3b6a2e7c1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('rule_review') as batch:
        batch.add_column(sa.Column('rating', sa.Integer(), nullable=True))
        batch.add_column(sa.Column('written_with', sa.String(16), nullable=True))


def downgrade():
    with op.batch_alter_table('rule_review') as batch:
        batch.drop_column('written_with')
        batch.drop_column('rating')
