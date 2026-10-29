"""a user in several organisations: user_organisation link table (existing assignments kept), user.organisation_id dropped

Revision ID: f4c9d2a7e5b8
Revises: e3b8f1c6a4d2
Create Date: 2026-10-29
"""
from alembic import op
import sqlalchemy as sa

revision = 'f4c9d2a7e5b8'
down_revision = 'e3b8f1c6a4d2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_organisation',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('organisation_id', sa.Integer(), sa.ForeignKey('organisation.id', ondelete='CASCADE'),
                  primary_key=True),
    )
    op.create_index('ix_user_organisation_organisation_id', 'user_organisation', ['organisation_id'])
    # keep every assignment made so far
    op.execute('INSERT INTO user_organisation (user_id, organisation_id) '
               'SELECT id, organisation_id FROM "user" WHERE organisation_id IS NOT NULL')
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_constraint('fk_user_organisation_id', type_='foreignkey')
        batch_op.drop_index('ix_user_organisation_id')
        batch_op.drop_column('organisation_id')


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('organisation_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_user_organisation_id', ['organisation_id'], unique=False)
        batch_op.create_foreign_key('fk_user_organisation_id', 'organisation', ['organisation_id'], ['id'],
                                    ondelete='SET NULL')
    # back to one organisation per user: the lowest id
    op.execute('UPDATE "user" SET organisation_id = (SELECT MIN(organisation_id) FROM user_organisation '
               'WHERE user_organisation.user_id = "user".id)')
    op.drop_index('ix_user_organisation_organisation_id', table_name='user_organisation')
    op.drop_table('user_organisation')
