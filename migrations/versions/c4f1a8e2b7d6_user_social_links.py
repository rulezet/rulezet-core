"""user.social_links — more profile links (LinkedIn, Bluesky, YouTube…), setting user.social_links (only adds)

Revision ID: c4f1a8e2b7d6
Revises: a6d8e2f4b9c1
"""
from alembic import op
import sqlalchemy as sa

revision = 'c4f1a8e2b7d6'
down_revision = 'a6d8e2f4b9c1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('social_links', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('social_links')
