"""rule reviews (only adds a table)

Revision ID: c8e2a5f1d9b4
Revises: b6d3e8a1c4f9
"""
from alembic import op
import sqlalchemy as sa

revision = 'c8e2a5f1d9b4'
down_revision = 'b6d3e8a1c4f9'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'rule_review',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(36), nullable=False),
        sa.Column('rule_id', sa.Integer(), sa.ForeignKey('rule.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('verdict', sa.String(20), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime()),
    )
    op.create_index('ix_rule_review_uuid', 'rule_review', ['uuid'], unique=True)
    op.create_index('ix_rule_review_rule_id', 'rule_review', ['rule_id'])
    op.create_index('ix_rule_review_user_id', 'rule_review', ['user_id'])


def downgrade():
    op.drop_table('rule_review')
