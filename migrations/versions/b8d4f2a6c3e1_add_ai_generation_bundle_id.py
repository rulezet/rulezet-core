"""add ai_generation.bundle_id (AI bundle analysis — agent config is seeded by --seed-defaults)

Revision ID: b8d4f2a6c3e1
Revises: a7c3e9f1d2b4
Create Date: 2026-09-25 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8d4f2a6c3e1'
down_revision = 'a7c3e9f1d2b4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('ai_generation', schema=None) as batch_op:
        batch_op.add_column(sa.Column('bundle_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_ai_generation_bundle_id'), ['bundle_id'], unique=False)
        batch_op.create_foreign_key('fk_ai_generation_bundle_id', 'bundle', ['bundle_id'], ['id'], ondelete='CASCADE')


def downgrade():
    with op.batch_alter_table('ai_generation', schema=None) as batch_op:
        batch_op.drop_constraint('fk_ai_generation_bundle_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_ai_generation_bundle_id'))
        batch_op.drop_column('bundle_id')
