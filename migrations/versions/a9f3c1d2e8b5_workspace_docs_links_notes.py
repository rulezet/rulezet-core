"""add workspace documents, links, and rule notes

Revision ID: a9f3c1d2e8b5
Revises: 8c573ad2ff74
Create Date: 2026-06-25 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'a9f3c1d2e8b5'
down_revision = '8c573ad2ff74'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    # Add note column to workspace_rule
    if 'workspace_rule' in existing_tables:
        wr_columns = {col['name'] for col in inspector.get_columns('workspace_rule')}
        if 'note' not in wr_columns:
            with op.batch_alter_table('workspace_rule', schema=None) as batch_op:
                batch_op.add_column(sa.Column('note', sa.Text(), nullable=True))

    # Create workspace_document table
    if 'workspace_document' not in existing_tables:
        op.create_table('workspace_document',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('workspace_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False, server_default='Untitled'),
            sa.Column('content', sa.Text(), nullable=False, server_default=''),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )

    # Create workspace_link table
    if 'workspace_link' not in existing_tables:
        op.create_table('workspace_link',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('workspace_id', sa.Integer(), nullable=False),
            sa.Column('title', sa.String(length=200), nullable=False),
            sa.Column('url', sa.String(length=1000), nullable=False),
            sa.Column('description', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id')
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'workspace_link' in existing_tables:
        op.drop_table('workspace_link')

    if 'workspace_document' in existing_tables:
        op.drop_table('workspace_document')

    if 'workspace_rule' in existing_tables:
        wr_columns = {col['name'] for col in inspector.get_columns('workspace_rule')}
        if 'note' in wr_columns:
            with op.batch_alter_table('workspace_rule', schema=None) as batch_op:
                batch_op.drop_column('note')
