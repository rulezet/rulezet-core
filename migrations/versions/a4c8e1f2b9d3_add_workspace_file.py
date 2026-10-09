"""add WorkspaceFile (images / PDF / office files attached to a workspace)

Revision ID: a4c8e1f2b9d3
Revises: d7f3b9a2e5c8
Create Date: 2026-10-09 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a4c8e1f2b9d3'
down_revision = 'd7f3b9a2e5c8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('workspace_file',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('uuid', sa.String(length=36), nullable=False),
    sa.Column('workspace_id', sa.Integer(), nullable=False),
    sa.Column('original_name', sa.String(length=255), nullable=False),
    sa.Column('stored_name', sa.String(length=255), nullable=False),
    sa.Column('mime_type', sa.String(length=128), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('uploaded_by', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['uploaded_by'], ['user.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('workspace_file', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workspace_file_uuid'), ['uuid'], unique=True)
        batch_op.create_index(batch_op.f('ix_workspace_file_workspace_id'), ['workspace_id'], unique=False)


def downgrade():
    with op.batch_alter_table('workspace_file', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workspace_file_workspace_id'))
        batch_op.drop_index(batch_op.f('ix_workspace_file_uuid'))
    op.drop_table('workspace_file')
