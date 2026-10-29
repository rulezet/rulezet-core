"""organisation: created by admins, users assigned to one (informative, shown on the profile and the UserChip)

Revision ID: d7a2c4e9b1f3
Revises: c5f1a8e3d2b7
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa

revision = 'd7a2c4e9b1f3'
down_revision = 'c5f1a8e3d2b7'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'organisation',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(length=100), nullable=False, unique=True),
        sa.Column('website', sa.String(length=256), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('user.id', ondelete='SET NULL'), nullable=True),
    )
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('organisation_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_user_organisation_id', ['organisation_id'], unique=False)
        batch_op.create_foreign_key('fk_user_organisation_id', 'organisation', ['organisation_id'], ['id'],
                                    ondelete='SET NULL')


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint('fk_user_organisation_id', type_='foreignkey')
        batch_op.drop_index('ix_user_organisation_id')
        batch_op.drop_column('organisation_id')
    op.drop_table('organisation')
