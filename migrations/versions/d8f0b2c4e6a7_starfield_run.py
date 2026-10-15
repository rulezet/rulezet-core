"""starfield_run: one row per finished Starfield run (admin score tracking)

Revision ID: d8f0b2c4e6a7
Revises: c7e9a1b3d5f6
Create Date: 2026-10-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8f0b2c4e6a7'
down_revision = 'c7e9a1b3d5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'starfield_run',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('player_id', sa.String(length=36), nullable=False),
        sa.Column('mode', sa.String(length=10), nullable=False),
        sa.Column('world', sa.Integer(), nullable=True),
        sa.Column('level_index', sa.Integer(), nullable=True),
        sa.Column('level_name', sa.String(length=80), nullable=True),
        sa.Column('level_kind', sa.String(length=20), nullable=True),
        sa.Column('won', sa.Boolean(), nullable=False),
        sa.Column('reason', sa.String(length=120), nullable=True),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('stars', sa.Integer(), nullable=False),
        sa.Column('wave', sa.Integer(), nullable=True),
        sa.Column('kills', sa.Integer(), nullable=False),
        sa.Column('hits', sa.Integer(), nullable=False),
        sa.Column('max_combo', sa.Integer(), nullable=False),
        sa.Column('bytes', sa.Integer(), nullable=False),
        sa.Column('time_s', sa.Integer(), nullable=False),
        sa.Column('ship', sa.String(length=20), nullable=True),
        sa.Column('difficulty', sa.String(length=20), nullable=True),
        sa.Column('controls', sa.String(length=10), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    for col in ('uuid', 'user_id', 'player_id', 'mode', 'score', 'ship', 'created_at'):
        op.create_index(f'ix_starfield_run_{col}', 'starfield_run', [col], unique=(col == 'uuid'))


def downgrade():
    op.drop_table('starfield_run')
