"""add workspace_bundle table (bundles collected in a workspace)

Revision ID: a7c3e9f1d2b4
Revises: f5b2d8e4c1a9
Create Date: 2026-09-25 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7c3e9f1d2b4'
down_revision = 'f5b2d8e4c1a9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'workspace_bundle',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('bundle_id', sa.Integer(), nullable=False),
        sa.Column('added_at', sa.DateTime(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['bundle_id'], ['bundle.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'bundle_id', name='uq_workspace_bundle'),
    )
    with op.batch_alter_table('workspace_bundle', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workspace_bundle_workspace_id'), ['workspace_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_workspace_bundle_bundle_id'), ['bundle_id'], unique=False)

    # Carry over the existing "exported from this workspace" links so those
    # bundles keep showing in their workspace's Bundles tab.
    op.execute(
        "INSERT INTO workspace_bundle (workspace_id, bundle_id, added_at) "
        "SELECT source_workspace_id, id, created_at FROM bundle "
        "WHERE source_workspace_id IS NOT NULL"
    )


def downgrade():
    with op.batch_alter_table('workspace_bundle', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workspace_bundle_bundle_id'))
        batch_op.drop_index(batch_op.f('ix_workspace_bundle_workspace_id'))
    op.drop_table('workspace_bundle')
