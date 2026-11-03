"""calendar reminder recipients

Revision ID: 7c1e9b4d2a60
Revises: 2ac4ad5faf2b
Create Date: 2026-11-03

"""
from alembic import op
import sqlalchemy as sa


revision = '7c1e9b4d2a60'
down_revision = '2ac4ad5faf2b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('admin_calendar_entry', schema=None) as batch_op:
        batch_op.add_column(sa.Column('notif_to', sa.String(length=10), nullable=False, server_default='admins'))
        batch_op.add_column(sa.Column('email_to', sa.String(length=10), nullable=False, server_default='me'))
        batch_op.add_column(sa.Column('emails', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('admin_calendar_entry', schema=None) as batch_op:
        batch_op.drop_column('emails')
        batch_op.drop_column('email_to')
        batch_op.drop_column('notif_to')
