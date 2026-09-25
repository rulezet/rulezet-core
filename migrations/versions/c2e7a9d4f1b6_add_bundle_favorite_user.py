"""add bundle_favorite_user table (users' favorite bundles)

Revision ID: c2e7a9d4f1b6
Revises: b8d4f2a6c3e1
Create Date: 2026-09-25 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c2e7a9d4f1b6'
down_revision = 'b8d4f2a6c3e1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'bundle_favorite_user',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('bundle_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['bundle_id'], ['bundle.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'bundle_id', name='uq_bundle_favorite_user'),
    )
    with op.batch_alter_table('bundle_favorite_user', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_bundle_favorite_user_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_bundle_favorite_user_bundle_id'), ['bundle_id'], unique=False)


def downgrade():
    with op.batch_alter_table('bundle_favorite_user', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_bundle_favorite_user_bundle_id'))
        batch_op.drop_index(batch_op.f('ix_bundle_favorite_user_user_id'))
    op.drop_table('bundle_favorite_user')
