"""add auth_provider column to user

Revision ID: bb68e19bd66a
Revises: 1214efa032bb
Create Date: 2026-09-08 11:09:33.638433

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'bb68e19bd66a'
down_revision = '1214efa032bb'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    user_cols = {c['name'] for c in inspector.get_columns('user')}

    if 'auth_provider' not in user_cols:
        op.add_column('user', sa.Column('auth_provider', sa.String(32), nullable=True, server_default='local'))

    if 'auth_data' not in user_cols:
        op.add_column('user', sa.Column('auth_data', sa.String(64), nullable=True))
        op.create_index(op.f('ix_user_auth_data'), 'user', ['auth_data'], unique=False)


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    user_cols = {c['name'] for c in inspector.get_columns('user')}

    if 'auth_data' in user_cols:
        op.drop_index(op.f('ix_user_auth_data'), table_name='user')
        op.drop_column('user', 'auth_data')

    if 'auth_provider' in user_cols:
        op.drop_column('user', 'auth_provider')
