"""add bundle_history table

Revision ID: b7c3e1f2a9d4
Revises: aaa9fcaae28c
Create Date: 2026-09-24 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7c3e1f2a9d4'
down_revision = 'aaa9fcaae28c'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'bundle_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('bundle_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=32), nullable=False),
        sa.Column('summary', sa.String(length=512), nullable=True),
        sa.Column('changes', sa.JSON(), nullable=True),
        sa.Column('old_snapshot', sa.JSON(), nullable=True),
        sa.Column('new_snapshot', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['bundle_id'], ['bundle.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('bundle_history', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_bundle_history_uuid'), ['uuid'], unique=True)
        batch_op.create_index(batch_op.f('ix_bundle_history_bundle_id'), ['bundle_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_bundle_history_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_bundle_history_action'), ['action'], unique=False)
        batch_op.create_index(batch_op.f('ix_bundle_history_created_at'), ['created_at'], unique=False)


def downgrade():
    with op.batch_alter_table('bundle_history', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_bundle_history_created_at'))
        batch_op.drop_index(batch_op.f('ix_bundle_history_action'))
        batch_op.drop_index(batch_op.f('ix_bundle_history_user_id'))
        batch_op.drop_index(batch_op.f('ix_bundle_history_bundle_id'))
        batch_op.drop_index(batch_op.f('ix_bundle_history_uuid'))
    op.drop_table('bundle_history')
