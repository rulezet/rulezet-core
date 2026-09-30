"""give Imported tags (rule authors' own tags, GitHub #70) their orange colour and user-tag icon

Imported tags created before they got a colour had none, so every page
showed them in the default grey, and carried the old fa-file-import icon.
Data-only: sets the colour and icon on those tags.

Revision ID: c3e8a1f5d7b2
Revises: a9c4e6f1b2d8
Create Date: 2026-09-30 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'c3e8a1f5d7b2'
down_revision = 'a9c4e6f1b2d8'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("UPDATE tag SET color = '#fd7e14' WHERE source = 'Imported' AND (color IS NULL OR color = '')")
    op.execute("UPDATE tag SET icon = 'fa-user-tag' WHERE source = 'Imported' AND (icon IS NULL OR icon = 'fa-file-import')")


def downgrade():
    op.execute("UPDATE tag SET color = NULL WHERE source = 'Imported' AND color = '#fd7e14'")
    op.execute("UPDATE tag SET icon = 'fa-file-import' WHERE source = 'Imported' AND icon = 'fa-user-tag'")
