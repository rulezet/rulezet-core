"""add bundle_release table (versioned, frozen bundle releases)

Revision ID: d9f1b3c5a7e2
Revises: c4d8a2b6e1f7
Create Date: 2026-09-24 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd9f1b3c5a7e2'
down_revision = 'c4d8a2b6e1f7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'bundle_release',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('bundle_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('version', sa.String(length=40), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('rule_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('file_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('health_score', sa.Integer(), nullable=True),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['bundle_id'], ['bundle.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('bundle_id', 'version', name='uq_bundle_release_version'),
    )
    with op.batch_alter_table('bundle_release', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_bundle_release_uuid'), ['uuid'], unique=True)
        batch_op.create_index(batch_op.f('ix_bundle_release_bundle_id'), ['bundle_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_bundle_release_created_at'), ['created_at'], unique=False)


def downgrade():
    with op.batch_alter_table('bundle_release', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_bundle_release_created_at'))
        batch_op.drop_index(batch_op.f('ix_bundle_release_bundle_id'))
        batch_op.drop_index(batch_op.f('ix_bundle_release_uuid'))
    op.drop_table('bundle_release')
