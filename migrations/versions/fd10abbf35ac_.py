"""empty message

Revision ID: fd10abbf35ac
Revises: e1a3c5e7f9b2
Create Date: 2026-10-15 12:33:38.967562

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fd10abbf35ac'
down_revision = 'e1a3c5e7f9b2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('nightshift_case_run',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('uuid', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('player_id', sa.String(length=36), nullable=False),
    sa.Column('case_id', sa.String(length=40), nullable=False),
    sa.Column('evidence', sa.JSON(), nullable=True),
    sa.Column('hints_used', sa.Integer(), nullable=False),
    sa.Column('tests', sa.Integer(), nullable=False),
    sa.Column('failed_deploys', sa.Integer(), nullable=False),
    sa.Column('closed', sa.Boolean(), nullable=False),
    sa.Column('score', sa.Integer(), nullable=False),
    sa.Column('stars', sa.Integer(), nullable=False),
    sa.Column('score_details', sa.JSON(), nullable=True),
    sa.Column('rule', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('last_test_at', sa.DateTime(), nullable=True),
    sa.Column('closed_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('nightshift_case_run', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_nightshift_case_run_case_id'), ['case_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_nightshift_case_run_closed'), ['closed'], unique=False)
        batch_op.create_index(batch_op.f('ix_nightshift_case_run_created_at'), ['created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_nightshift_case_run_player_id'), ['player_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_nightshift_case_run_score'), ['score'], unique=False)
        batch_op.create_index(batch_op.f('ix_nightshift_case_run_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_nightshift_case_run_uuid'), ['uuid'], unique=True)

    op.create_table('nightshift_attempt',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('run_id', sa.Integer(), nullable=False),
    sa.Column('kind', sa.String(length=10), nullable=False),
    sa.Column('rule', sa.Text(), nullable=False),
    sa.Column('error', sa.String(length=300), nullable=True),
    sa.Column('tp', sa.Integer(), nullable=False),
    sa.Column('fp', sa.Integer(), nullable=False),
    sa.Column('fn', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['run_id'], ['nightshift_case_run.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('nightshift_attempt', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_nightshift_attempt_run_id'), ['run_id'], unique=False)


def downgrade():
    with op.batch_alter_table('nightshift_attempt', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_nightshift_attempt_run_id'))
    op.drop_table('nightshift_attempt')

    with op.batch_alter_table('nightshift_case_run', schema=None) as batch_op:
        for name in ('uuid', 'user_id', 'score', 'player_id', 'created_at', 'closed', 'case_id'):
            batch_op.drop_index(batch_op.f(f'ix_nightshift_case_run_{name}'))
    op.drop_table('nightshift_case_run')
