"""app_setting + app_setting_history: admin-editable settings (values that used to be hard-coded) and their history

Revision ID: c7e9a1b3d5f6
Revises: b4d6f8a0c2e3
Create Date: 2026-10-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7e9a1b3d5f6'
down_revision = 'b4d6f8a0c2e3'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'app_setting',
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('base_value', sa.JSON(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('updated_by_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('key'),
    )
    op.create_table(
        'app_setting_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('key', sa.String(length=128), nullable=False),
        sa.Column('action', sa.String(length=16), nullable=False),
        sa.Column('value', sa.JSON(), nullable=True),
        sa.Column('base_value', sa.JSON(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_app_setting_history_key', 'app_setting_history', ['key'])
    op.create_index('ix_app_setting_history_created_at', 'app_setting_history', ['created_at'])


def downgrade():
    op.drop_table('app_setting_history')
    op.drop_table('app_setting')
