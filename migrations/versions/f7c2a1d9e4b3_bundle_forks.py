"""bundle forks and merge requests (only adds)

Revision ID: f7c2a1d9e4b3
Revises: e5b1f8c3a9d2
"""
from alembic import op
import sqlalchemy as sa

revision = 'f7c2a1d9e4b3'
down_revision = 'e5b1f8c3a9d2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('bundle', schema=None) as batch_op:
        batch_op.add_column(sa.Column('forked_from_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('forked_from_uuid', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('fork_base_snapshot', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('fork_base_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('accepts_proposals', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.create_index('ix_bundle_forked_from_id', ['forked_from_id'])
        batch_op.create_index('ix_bundle_forked_from_uuid', ['forked_from_uuid'])
        batch_op.create_foreign_key('fk_bundle_forked_from_id', 'bundle', ['forked_from_id'], ['id'], ondelete='SET NULL')

    op.create_table(
        'bundle_fork_rule',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('bundle_id', sa.Integer(), sa.ForeignKey('bundle.id', ondelete='CASCADE'), nullable=False),
        sa.Column('original_rule_uuid', sa.String(length=255), nullable=False),
        sa.Column('copy_rule_id', sa.Integer(), sa.ForeignKey('rule.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('bundle_id', 'copy_rule_id', name='uq_bundle_fork_rule_copy'),
    )
    op.create_index('ix_bundle_fork_rule_bundle_id', 'bundle_fork_rule', ['bundle_id'])
    op.create_index('ix_bundle_fork_rule_original_rule_uuid', 'bundle_fork_rule', ['original_rule_uuid'])
    op.create_index('ix_bundle_fork_rule_copy_rule_id', 'bundle_fork_rule', ['copy_rule_id'])

    op.create_table(
        'bundle_merge_request',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('source_bundle_id', sa.Integer(), sa.ForeignKey('bundle.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_bundle_uuid', sa.String(length=255), nullable=True),
        sa.Column('target_bundle_id', sa.Integer(), sa.ForeignKey('bundle.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='SET NULL'), nullable=True),
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('items', sa.JSON(), nullable=True),
        sa.Column('base_snapshot', sa.JSON(), nullable=True),
        sa.Column('computed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('merged_summary', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_bundle_merge_request_uuid', 'bundle_merge_request', ['uuid'], unique=True)
    op.create_index('ix_bundle_merge_request_source_bundle_id', 'bundle_merge_request', ['source_bundle_id'])
    op.create_index('ix_bundle_merge_request_target_bundle_id', 'bundle_merge_request', ['target_bundle_id'])
    op.create_index('ix_bundle_merge_request_user_id', 'bundle_merge_request', ['user_id'])
    op.create_index('ix_bundle_merge_request_status', 'bundle_merge_request', ['status'])
    op.create_index('ix_bundle_merge_request_created_at', 'bundle_merge_request', ['created_at'])

    with op.batch_alter_table('notification_preference', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pref_bundle_fork', sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade():
    with op.batch_alter_table('notification_preference', schema=None) as batch_op:
        batch_op.drop_column('pref_bundle_fork')
    op.drop_table('bundle_merge_request')
    op.drop_table('bundle_fork_rule')
    with op.batch_alter_table('bundle', schema=None) as batch_op:
        batch_op.drop_constraint('fk_bundle_forked_from_id', type_='foreignkey')
        batch_op.drop_index('ix_bundle_forked_from_uuid')
        batch_op.drop_index('ix_bundle_forked_from_id')
        batch_op.drop_column('accepts_proposals')
        batch_op.drop_column('fork_base_at')
        batch_op.drop_column('fork_base_snapshot')
        batch_op.drop_column('forked_from_uuid')
        batch_op.drop_column('forked_from_id')
