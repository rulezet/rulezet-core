"""user identity verification: an admin confirms a person is who they claim to be, with a justification and the history

Revision ID: c5f1a8e3d2b7
Revises: b8e4d0f2a6c1
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa

revision = 'c5f1a8e3d2b7'
down_revision = 'b8e4d0f2a6c1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('identity_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.create_table(
        'user_identity_verification',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('verified', sa.Boolean(), nullable=False),
        sa.Column('justification', sa.Text(), nullable=False),
        sa.Column('by_user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_user_identity_verification_user_id', 'user_identity_verification', ['user_id'])


def downgrade():
    op.drop_index('ix_user_identity_verification_user_id', table_name='user_identity_verification')
    op.drop_table('user_identity_verification')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('identity_verified')
