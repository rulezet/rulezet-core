"""rule resources (notes and external links)

Revision ID: 1567a80f1c2c
Revises: 7c1e9b4d2a60
Create Date: 2026-11-10 10:52:36.810449

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1567a80f1c2c'
down_revision = '7c1e9b4d2a60'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'rule_resource',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('kind', sa.String(length=10), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('url', sa.String(length=2000), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['rule_id'], ['rule.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('rule_resource', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_rule_resource_uuid'), ['uuid'], unique=True)
        batch_op.create_index(batch_op.f('ix_rule_resource_rule_id'), ['rule_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_rule_resource_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_rule_resource_created_at'), ['created_at'], unique=False)


def downgrade():
    with op.batch_alter_table('rule_resource', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_rule_resource_created_at'))
        batch_op.drop_index(batch_op.f('ix_rule_resource_user_id'))
        batch_op.drop_index(batch_op.f('ix_rule_resource_rule_id'))
        batch_op.drop_index(batch_op.f('ix_rule_resource_uuid'))
    op.drop_table('rule_resource')
