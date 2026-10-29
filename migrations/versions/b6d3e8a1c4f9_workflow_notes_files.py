"""workflow notes, attached files and read-only share key (only adds)

Revision ID: b6d3e8a1c4f9
Revises: a9c4e2f7b3d1
"""
from alembic import op
import sqlalchemy as sa

revision = 'b6d3e8a1c4f9'
down_revision = 'a9c4e2f7b3d1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('admin_workflow') as batch:
        batch.add_column(sa.Column('share_key', sa.String(64), nullable=True))
        batch.create_unique_constraint('uq_admin_workflow_share_key', ['share_key'])
    op.create_table(
        'admin_workflow_note',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uuid', sa.String(36), unique=True),
        sa.Column('workflow_id', sa.Integer(), sa.ForeignKey('admin_workflow.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workflow_run_id', sa.Integer(), sa.ForeignKey('admin_workflow_run.id', ondelete='SET NULL'), nullable=True),
        sa.Column('author_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('pinned', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime()),
        sa.Column('updated_at', sa.DateTime()),
    )
    op.create_index('ix_admin_workflow_note_uuid', 'admin_workflow_note', ['uuid'], unique=True)
    op.create_index('ix_admin_workflow_note_workflow_id', 'admin_workflow_note', ['workflow_id'])
    op.create_table(
        'admin_workflow_file',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uuid', sa.String(36), unique=True),
        sa.Column('workflow_id', sa.Integer(), sa.ForeignKey('admin_workflow.id', ondelete='CASCADE'), nullable=False),
        sa.Column('uploader_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='SET NULL'), nullable=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('stored_name', sa.String(64), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_admin_workflow_file_uuid', 'admin_workflow_file', ['uuid'], unique=True)
    op.create_index('ix_admin_workflow_file_workflow_id', 'admin_workflow_file', ['workflow_id'])


def downgrade():
    op.drop_table('admin_workflow_file')
    op.drop_table('admin_workflow_note')
    with op.batch_alter_table('admin_workflow') as batch:
        batch.drop_constraint('uq_admin_workflow_share_key', type_='unique')
        batch.drop_column('share_key')
