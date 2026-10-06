"""ai_provider: several AI backends (Ollama, Claude, ChatGPT, OpenAI-compatible), one active

Revision ID: e7a2c4f9b1d6
Revises: d4f2b7e9c1a3
Create Date: 2026-10-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7a2c4f9b1d6'
down_revision = 'd4f2b7e9c1a3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ai_provider',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('base_url', sa.String(length=512), nullable=True),
        sa.Column('api_key_enc', sa.Text(), nullable=True),
        sa.Column('default_model', sa.String(length=128), nullable=True),
        sa.Column('remote_allowed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('last_test_at', sa.DateTime(), nullable=True),
        sa.Column('last_test_ok', sa.Boolean(), nullable=True),
        sa.Column('last_test_message', sa.String(length=300), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    with op.batch_alter_table('ai_provider', schema=None) as batch_op:
        batch_op.create_index('ix_ai_provider_uuid', ['uuid'], unique=True)
        batch_op.create_index('ix_ai_provider_is_active', ['is_active'], unique=False)
    # No data step: the first provider is seeded from instance_config's
    # Ollama settings on first use (ai_core.get_active_provider), so the
    # instance keeps running on Ollama exactly as before.


def downgrade():
    with op.batch_alter_table('ai_provider', schema=None) as batch_op:
        batch_op.drop_index('ix_ai_provider_is_active')
        batch_op.drop_index('ix_ai_provider_uuid')
    op.drop_table('ai_provider')
