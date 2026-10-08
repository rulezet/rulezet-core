"""ai_provider.workspace_id — anthropic-workspace-id header for organization-level Claude keys

Revision ID: f3b8d2a6c4e1
Revises: e7a2c4f9b1d6
Create Date: 2026-10-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3b8d2a6c4e1'
down_revision = 'e7a2c4f9b1d6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('ai_provider', schema=None) as batch_op:
        batch_op.add_column(sa.Column('workspace_id', sa.String(length=128), nullable=True))


def downgrade():
    with op.batch_alter_table('ai_provider', schema=None) as batch_op:
        batch_op.drop_column('workspace_id')
