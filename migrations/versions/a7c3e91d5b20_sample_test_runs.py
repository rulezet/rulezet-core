"""tests on sample sets: run states and per-rule results

Revision ID: a7c3e91d5b20
Revises: fd10abbf35ac
Create Date: 2026-10-26 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7c3e91d5b20'
down_revision = 'fd10abbf35ac'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('sample_test_run',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.String(length=32), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('format', sa.String(length=32), nullable=False),
        sa.Column('origin', sa.String(length=16), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('state', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('sample_test_run', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_sample_test_run_run_id'), ['run_id'], unique=True)
        batch_op.create_index(batch_op.f('ix_sample_test_run_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_sample_test_run_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_sample_test_run_created_at'), ['created_at'], unique=False)

    op.create_table('rule_sample_result',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('total', sa.Integer(), nullable=False),
        sa.Column('detected', sa.Integer(), nullable=False),
        sa.Column('missed', sa.Integer(), nullable=False),
        sa.Column('false_positives', sa.Integer(), nullable=False),
        sa.Column('errors', sa.Integer(), nullable=False),
        sa.Column('sets', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['rule_id'], ['rule.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['run_id'], ['sample_test_run.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('rule_sample_result', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_rule_sample_result_rule_id'), ['rule_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_rule_sample_result_run_id'), ['run_id'], unique=False)


def downgrade():
    op.drop_table('rule_sample_result')
    op.drop_table('sample_test_run')
