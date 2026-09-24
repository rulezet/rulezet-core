"""add bundle share_token (private share link)

Revision ID: c4d8a2b6e1f7
Revises: b7c3e1f2a9d4
Create Date: 2026-09-24 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4d8a2b6e1f7'
down_revision = 'b7c3e1f2a9d4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('bundle', schema=None) as batch_op:
        batch_op.add_column(sa.Column('share_token', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('share_token_created_at', sa.DateTime(), nullable=True))
        batch_op.create_index(batch_op.f('ix_bundle_share_token'), ['share_token'], unique=True)


def downgrade():
    with op.batch_alter_table('bundle', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_bundle_share_token'))
        batch_op.drop_column('share_token_created_at')
        batch_op.drop_column('share_token')
