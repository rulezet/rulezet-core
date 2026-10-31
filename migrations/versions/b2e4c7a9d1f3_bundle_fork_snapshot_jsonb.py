"""bundle.fork_base_snapshot as JSONB on PostgreSQL — plain JSON broke every SELECT DISTINCT on bundles
(no equality operator for json), e.g. the bundle count of every rule page

Revision ID: b2e4c7a9d1f3
Revises: a8d3f6b1c2e9
"""
from alembic import op

revision = 'b2e4c7a9d1f3'
down_revision = 'a8d3f6b1c2e9'
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('ALTER TABLE bundle ALTER COLUMN fork_base_snapshot TYPE jsonb USING fork_base_snapshot::jsonb')


def downgrade():
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('ALTER TABLE bundle ALTER COLUMN fork_base_snapshot TYPE json USING fork_base_snapshot::json')
