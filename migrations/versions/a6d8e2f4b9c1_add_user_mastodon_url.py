"""add Mastodon profile URL to user

Revision ID: a6d8e2f4b9c1
Revises: b2e4c7a9d1f3
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa

revision = 'a6d8e2f4b9c1'
down_revision = 'b2e4c7a9d1f3'  # after the AI provenance and JSONB migrations merged before it
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('mastodon_url', sa.String(length=256), nullable=True))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('mastodon_url')
