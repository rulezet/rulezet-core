"""user collections: private folders of rules / bundles with note, status, reminder

Revision ID: 03d507bd10ab
Revises: 3c9e5f7a2b01
Create Date: 2026-11-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '03d507bd10ab'
down_revision = '3c9e5f7a2b01'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_collection',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_id', sa.Integer(), sa.ForeignKey('user_collection.id', ondelete='CASCADE'), nullable=True),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('icon', sa.String(length=60), nullable=True),
        sa.Column('color', sa.String(length=20), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_collection_user_id', 'user_collection', ['user_id'])
    op.create_index('ix_user_collection_parent_id', 'user_collection', ['parent_id'])

    op.create_table(
        'user_collection_item',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('collection_id', sa.Integer(), sa.ForeignKey('user_collection.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rule_id', sa.Integer(), sa.ForeignKey('rule.id', ondelete='CASCADE'), nullable=True),
        sa.Column('bundle_id', sa.Integer(), sa.ForeignKey('bundle.id', ondelete='CASCADE'), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='todo'),
        sa.Column('remind_at', sa.DateTime(), nullable=True),
        sa.Column('reminded_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('collection_id', 'rule_id', name='uq_collection_rule'),
        sa.UniqueConstraint('collection_id', 'bundle_id', name='uq_collection_bundle'),
    )
    for col in ('collection_id', 'user_id', 'rule_id', 'bundle_id', 'remind_at'):
        op.create_index(f'ix_user_collection_item_{col}', 'user_collection_item', [col])


def downgrade():
    op.drop_table('user_collection_item')
    op.drop_table('user_collection')
