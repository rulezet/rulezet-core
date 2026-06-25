"""add workspace other field

Revision ID: c3f8d2b5e1a7
Revises: b2e7f4a1c9d3
Create Date: 2026-06-25
"""
from alembic import op
import sqlalchemy as sa

revision = 'c3f8d2b5e1a7'
down_revision = 'b2e7f4a1c9d3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('workspace', sa.Column('other', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('workspace', 'other')
