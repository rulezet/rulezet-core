"""blog covers shipped with Rulezet moved from static/uploads/blog/vendor to static/images/blog

Revision ID: d8f1a3c5e7b9
Revises: c5e7a9b1d3f2
Create Date: 2026-10-09 18:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'd8f1a3c5e7b9'
down_revision = 'c5e7a9b1d3f2'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE blog_post SET cover_image_url = REPLACE(cover_image_url, "
               "'/static/uploads/blog/vendor/', '/static/images/blog/') "
               "WHERE cover_image_url LIKE '/static/uploads/blog/vendor/%'")


def downgrade():
    op.execute("UPDATE blog_post SET cover_image_url = REPLACE(cover_image_url, "
               "'/static/images/blog/', '/static/uploads/blog/vendor/') "
               "WHERE cover_image_url LIKE '/static/images/blog/%'")
