"""github_sync_schedule_repo: who the new rules of a scheduled repo belong to

Revision ID: f3b9d1e4a726
Revises: e5a2c7d9b148
Create Date: 2026-10-28 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3b9d1e4a726'
down_revision = 'e5a2c7d9b148'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('github_sync_schedule_repo', schema=None) as batch_op:
        batch_op.add_column(sa.Column('new_rule_owner_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_schedule_repo_new_rule_owner', 'user', ['new_rule_owner_id'], ['id'],
                                    ondelete='SET NULL')


def downgrade():
    with op.batch_alter_table('github_sync_schedule_repo', schema=None) as batch_op:
        batch_op.drop_constraint('fk_schedule_repo_new_rule_owner', type_='foreignkey')
        batch_op.drop_column('new_rule_owner_id')
