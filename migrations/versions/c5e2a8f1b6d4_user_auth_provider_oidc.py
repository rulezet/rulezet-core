"""user.auth_provider / user.auth_data — OIDC (SSO) login

auth_provider: 'local' (password) or 'oidc'. auth_data: the OIDC subject
('sub'), unique — the stable identity of an SSO account. Columns are only
added when missing, so a database that already ran the original PR #71
migration (bb68e19bd66a) upgrades cleanly; the unique index is (re)created
either way.

Revision ID: c5e2a8f1b6d4
Revises: a9c1e5f7d3b2
Create Date: 2026-10-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'c5e2a8f1b6d4'
down_revision = 'a9c1e5f7d3b2'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    cols = {c['name'] for c in inspector.get_columns('user')}
    indexes = {i['name'] for i in inspector.get_indexes('user')}
    had_pr_columns = 'auth_provider' in cols or 'auth_data' in cols

    with op.batch_alter_table('user', schema=None) as batch_op:
        if 'auth_provider' not in cols:
            batch_op.add_column(sa.Column('auth_provider', sa.String(length=32), nullable=False,
                                          server_default='local'))
        if 'auth_data' not in cols:
            batch_op.add_column(sa.Column('auth_data', sa.String(length=128), nullable=True))
        if 'ix_user_auth_data' in indexes:
            batch_op.drop_index('ix_user_auth_data')

    if had_pr_columns:
        # Coming from the original PR migration: bring its looser columns
        # (nullable auth_provider, String(64) auth_data) up to the model.
        op.execute("UPDATE \"user\" SET auth_provider = 'local' WHERE auth_provider IS NULL")
        with op.batch_alter_table('user', schema=None) as batch_op:
            batch_op.alter_column('auth_provider', existing_type=sa.String(length=32), nullable=False,
                                  server_default='local')
            batch_op.alter_column('auth_data', existing_type=sa.String(length=64), type_=sa.String(length=128))

    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.create_index('ix_user_auth_data', ['auth_data'], unique=True)


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_index('ix_user_auth_data')
        batch_op.drop_column('auth_data')
        batch_op.drop_column('auth_provider')
