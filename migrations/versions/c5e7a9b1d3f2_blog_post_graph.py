"""blog_post.graph — a Pivograph map attached to a blog post (+ graph_view: full / simple)

Revision ID: c5e7a9b1d3f2
Revises: b7d2e4f6a8c1
Create Date: 2026-10-09 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5e7a9b1d3f2'
down_revision = 'b7d2e4f6a8c1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('blog_post', schema=None) as batch_op:
        batch_op.add_column(sa.Column('graph', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('graph_view', sa.String(length=16), nullable=False, server_default='full'))


def downgrade():
    with op.batch_alter_table('blog_post', schema=None) as batch_op:
        batch_op.drop_column('graph_view')
        batch_op.drop_column('graph')
