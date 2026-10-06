"""AI provider monthly budget + per-run token usage / cost on ai_execution_log

Revision ID: a9c1e5f7d3b2
Revises: f3b8d2a6c4e1
Create Date: 2026-10-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a9c1e5f7d3b2'
down_revision = 'f3b8d2a6c4e1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('ai_provider', schema=None) as batch_op:
        batch_op.add_column(sa.Column('monthly_budget_usd', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('price_input_per_mtok', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('price_output_per_mtok', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('block_over_budget', sa.Boolean(), nullable=False, server_default=sa.false()))

    with op.batch_alter_table('ai_execution_log', schema=None) as batch_op:
        batch_op.add_column(sa.Column('provider_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('input_tokens', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('output_tokens', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('cost_usd', sa.Float(), nullable=True))
        batch_op.create_index('ix_ai_execution_log_provider_id', ['provider_id'], unique=False)
        batch_op.create_foreign_key('fk_ai_execution_log_provider_id', 'ai_provider', ['provider_id'], ['id'],
                                    ondelete='SET NULL')


def downgrade():
    with op.batch_alter_table('ai_execution_log', schema=None) as batch_op:
        batch_op.drop_constraint('fk_ai_execution_log_provider_id', type_='foreignkey')
        batch_op.drop_index('ix_ai_execution_log_provider_id')
        batch_op.drop_column('cost_usd')
        batch_op.drop_column('output_tokens')
        batch_op.drop_column('input_tokens')
        batch_op.drop_column('provider_id')

    with op.batch_alter_table('ai_provider', schema=None) as batch_op:
        batch_op.drop_column('block_over_budget')
        batch_op.drop_column('price_output_per_mtok')
        batch_op.drop_column('price_input_per_mtok')
        batch_op.drop_column('monthly_budget_usd')
