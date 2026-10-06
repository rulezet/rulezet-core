"""pivotick_graph_style.enabled / .renderer — admin on/off switch per graph
(rule, bundle, attack), and for rule/bundle which MISP→graph mapping draws it

Revision ID: d7f3b9a2e5c8
Revises: c5e2a8f1b6d4
Create Date: 2026-10-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7f3b9a2e5c8'
down_revision = 'c5e2a8f1b6d4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('pivotick_graph_style', schema=None) as batch_op:
        batch_op.add_column(sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column('renderer', sa.String(length=20), nullable=True))


def downgrade():
    with op.batch_alter_table('pivotick_graph_style', schema=None) as batch_op:
        batch_op.drop_column('renderer')
        batch_op.drop_column('enabled')
