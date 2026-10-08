"""add bundle_note table (community notes / known issues on bundles)

Revision ID: e3a7c9d1b5f8
Revises: d9f1b3c5a7e2
Create Date: 2026-09-24 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3a7c9d1b5f8'
down_revision = 'd9f1b3c5a7e2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'bundle_note',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('bundle_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=16), nullable=False, server_default='warning'),
        sa.Column('status', sa.String(length=16), nullable=False, server_default='open'),
        sa.Column('resolved_by_id', sa.Integer(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['bundle_id'], ['bundle.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_by_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('bundle_note', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_bundle_note_uuid'), ['uuid'], unique=True)
        batch_op.create_index(batch_op.f('ix_bundle_note_bundle_id'), ['bundle_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_bundle_note_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_bundle_note_status'), ['status'], unique=False)
        batch_op.create_index(batch_op.f('ix_bundle_note_created_at'), ['created_at'], unique=False)


def downgrade():
    with op.batch_alter_table('bundle_note', schema=None) as batch_op:
        for ix in ('created_at', 'status', 'user_id', 'bundle_id', 'uuid'):
            batch_op.drop_index(batch_op.f(f'ix_bundle_note_{ix}'))
    op.drop_table('bundle_note')
