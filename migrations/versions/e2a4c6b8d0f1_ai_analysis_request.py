"""ai_analysis_request: users ask for an AI analysis of a rule or a bundle

Revision ID: e2a4c6b8d0f1
Revises: d8f1a3c5e7b9
Create Date: 2026-10-09 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2a4c6b8d0f1'
down_revision = 'd8f1a3c5e7b9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'ai_analysis_request',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('target_type', sa.String(length=10), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=True),
        sa.Column('bundle_id', sa.Integer(), nullable=True),
        sa.Column('script', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('decided_by_id', sa.Integer(), nullable=True),
        sa.Column('decided_at', sa.DateTime(), nullable=True),
        sa.Column('decision_note', sa.Text(), nullable=True),
        sa.Column('job_uuid', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['rule_id'], ['rule.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['bundle_id'], ['bundle.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['decided_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('ai_analysis_request', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ai_analysis_request_uuid'), ['uuid'], unique=True)
        batch_op.create_index(batch_op.f('ix_ai_analysis_request_target_type'), ['target_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_ai_analysis_request_rule_id'), ['rule_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_ai_analysis_request_bundle_id'), ['bundle_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_ai_analysis_request_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_ai_analysis_request_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_ai_analysis_request_created_at'), ['created_at'], unique=False)


def downgrade():
    op.drop_table('ai_analysis_request')
