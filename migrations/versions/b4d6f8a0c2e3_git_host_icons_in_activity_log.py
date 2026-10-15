"""activity_log: git entries get their host's icon (GitHub, GitLab, Gitea…) instead of GitHub's

Revision ID: b4d6f8a0c2e3
Revises: a9c3e5f7b1d2
Create Date: 2026-10-15 00:00:00.000000

"""
import json

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4d6f8a0c2e3'
down_revision = 'a9c3e5f7b1d2'
branch_labels = None
depends_on = None


def upgrade():
    from app.core.utils.activity_log import _git_host_icon
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, icon, extra FROM activity_log WHERE icon IN ('fa-brands fa-github', 'fab fa-github')")).fetchall()
    for rid, icon, extra in rows:
        if isinstance(extra, str):
            try:
                extra = json.loads(extra)
            except ValueError:
                extra = None
        new_icon = _git_host_icon(icon, extra if isinstance(extra, dict) else None)
        if new_icon != icon:
            conn.execute(sa.text("UPDATE activity_log SET icon = :i WHERE id = :id"), {'i': new_icon, 'id': rid})


def downgrade():
    pass
