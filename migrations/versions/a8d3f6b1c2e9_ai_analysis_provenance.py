"""AI analysis provenance and request lifecycle — issues #88 / #89 (only adds)

Revision ID: a8d3f6b1c2e9
Revises: f7c2a1d9e4b3
"""
from alembic import op
import sqlalchemy as sa

revision = 'a8d3f6b1c2e9'
down_revision = 'f7c2a1d9e4b3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('ai_generation', schema=None) as b:
        b.add_column(sa.Column('content_hash', sa.String(length=64), nullable=True))
        b.add_column(sa.Column('request_id', sa.Integer(), nullable=True))
        b.add_column(sa.Column('job_uuid', sa.String(length=36), nullable=True))
        b.add_column(sa.Column('requested_by_id', sa.Integer(), nullable=True))
        b.add_column(sa.Column('approved_by_id', sa.Integer(), nullable=True))
        b.add_column(sa.Column('initiated_by_id', sa.Integer(), nullable=True))
        b.create_foreign_key('fk_ai_generation_request', 'ai_analysis_request', ['request_id'], ['id'], ondelete='SET NULL')
        b.create_foreign_key('fk_ai_generation_requested_by', 'user', ['requested_by_id'], ['id'], ondelete='SET NULL')
        b.create_foreign_key('fk_ai_generation_approved_by', 'user', ['approved_by_id'], ['id'], ondelete='SET NULL')
        b.create_foreign_key('fk_ai_generation_initiated_by', 'user', ['initiated_by_id'], ['id'], ondelete='SET NULL')
    with op.batch_alter_table('ai_analysis_request', schema=None) as b:
        b.add_column(sa.Column('input_content', sa.Text(), nullable=True))
        b.add_column(sa.Column('content_hash', sa.String(length=64), nullable=True))
        b.add_column(sa.Column('execution_status', sa.String(length=16), nullable=False, server_default='not_started'))
        b.add_column(sa.Column('executed_at', sa.DateTime(), nullable=True))
        b.add_column(sa.Column('generation_id', sa.Integer(), nullable=True))
        b.create_index('ix_ai_analysis_request_content_hash', ['content_hash'])
        b.create_foreign_key('fk_ai_analysis_request_generation', 'ai_generation', ['generation_id'], ['id'],
                             ondelete='SET NULL')
    # requests accepted before: their job ran (or not) — "completed" when it is done, else left to the
    # read-time check (effective status from the job)
    op.execute("UPDATE ai_analysis_request SET execution_status = 'queued' WHERE status = 'accepted'")


def downgrade():
    with op.batch_alter_table('ai_analysis_request', schema=None) as b:
        b.drop_constraint('fk_ai_analysis_request_generation', type_='foreignkey')
        b.drop_index('ix_ai_analysis_request_content_hash')
        for c in ('generation_id', 'executed_at', 'execution_status', 'content_hash', 'input_content'):
            b.drop_column(c)
    with op.batch_alter_table('ai_generation', schema=None) as b:
        for fk in ('fk_ai_generation_initiated_by', 'fk_ai_generation_approved_by', 'fk_ai_generation_requested_by',
                   'fk_ai_generation_request'):
            b.drop_constraint(fk, type_='foreignkey')
        for c in ('initiated_by_id', 'approved_by_id', 'requested_by_id', 'job_uuid', 'request_id', 'content_hash'):
            b.drop_column(c)
