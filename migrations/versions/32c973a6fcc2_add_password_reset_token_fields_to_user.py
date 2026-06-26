"""add password reset token fields to user

Revision ID: 32c973a6fcc2
Revises: c3f8d2b5e1a7
Create Date: 2026-06-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '32c973a6fcc2'
down_revision = 'c3f8d2b5e1a7'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    user_cols = {c['name'] for c in inspector.get_columns('user')}

    if 'password_reset_token' not in user_cols:
        op.add_column('user', sa.Column('password_reset_token', sa.String(64), nullable=True))
        op.create_index(op.f('ix_user_password_reset_token'), 'user', ['password_reset_token'], unique=False)

    if 'password_reset_expiration' not in user_cols:
        op.add_column('user', sa.Column('password_reset_expiration', sa.DateTime(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    user_cols = {c['name'] for c in inspector.get_columns('user')}

    if 'password_reset_expiration' in user_cols:
        op.drop_column('user', 'password_reset_expiration')

    if 'password_reset_token' in user_cols:
        op.drop_index(op.f('ix_user_password_reset_token'), table_name='user')
        op.drop_column('user', 'password_reset_token')
