"""git_provider on every git-related table (github | gitlab | gitea | bitbucket | generic)

Revision ID: a9c3e5f7b1d2
Revises: e2a4c6b8d0f1
Create Date: 2026-10-15 00:00:00.000000

"""
import json

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a9c3e5f7b1d2'
down_revision = 'e2a4c6b8d0f1'
branch_labels = None
depends_on = None


# table -> SQL giving (id, url) to classify
_TABLES = {
    'rule': "SELECT DISTINCT source FROM rule WHERE source LIKE 'http%' AND github_path IS NOT NULL",
    'invalid_rule_model': "SELECT DISTINCT url FROM invalid_rule_model WHERE url LIKE 'http%'",
    'github_repo': "SELECT DISTINCT url FROM github_repo",
    'github_proposal': "SELECT DISTINCT repo_url FROM github_proposal",
    'github_sync_schedule_repo': "SELECT DISTINCT repo_url FROM github_sync_schedule_repo",
    'rule_mirror_config': "SELECT DISTINCT repo_url FROM rule_mirror_config WHERE repo_url IS NOT NULL",
}
_URL_COLUMN = {
    'rule': 'source', 'invalid_rule_model': 'url', 'github_repo': 'url',
    'github_proposal': 'repo_url', 'github_sync_schedule_repo': 'repo_url', 'rule_mirror_config': 'repo_url',
}


def upgrade():
    for table in list(_TABLES) + ['importer_result', 'update_result']:
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(sa.Column('git_provider', sa.String(length=20), nullable=True))
            batch_op.create_index(f'ix_{table}_git_provider', ['git_provider'], unique=False)

    from app.features.rule.rule_format.utils_format.git_provider import detect_provider, is_git_repo_url
    conn = op.get_bind()

    # One UPDATE per distinct URL — a few thousand at most, not one per rule.
    for table, query in _TABLES.items():
        col = _URL_COLUMN[table]
        for (url,) in conn.execute(sa.text(query)).fetchall():
            if url and url.startswith(('http://', 'https://')):
                conn.execute(sa.text(f"UPDATE {table} SET git_provider = :p WHERE {col} = :u"),
                             {'p': detect_provider(url), 'u': url})
    # Rules with a git source but no github_path (manual rules pointing at a repo).
    for (url,) in conn.execute(sa.text(
            "SELECT DISTINCT source FROM rule WHERE git_provider IS NULL AND source LIKE 'http%'")).fetchall():
        if is_git_repo_url(url):
            conn.execute(sa.text("UPDATE rule SET git_provider = :p WHERE source = :u"),
                         {'p': detect_provider(url), 'u': url})

    for (rid, info) in conn.execute(sa.text("SELECT id, info FROM importer_result")).fetchall():
        try:
            url = (json.loads(info or '{}') or {}).get('repo_url')
        except (ValueError, AttributeError):
            url = None
        if url and url.startswith(('http://', 'https://')):
            conn.execute(sa.text("UPDATE importer_result SET git_provider = :p WHERE id = :i"),
                         {'p': detect_provider(url), 'i': rid})

    for (rid, mode, sources) in conn.execute(sa.text("SELECT id, mode, repo_sources FROM update_result")).fetchall():
        if mode == 'by_rule' or not sources:
            continue
        try:
            sources = json.loads(sources)
        except ValueError:
            continue
        if isinstance(sources, list):
            sources = next((x for x in sources if isinstance(x, str)), None)
        if isinstance(sources, str) and sources.startswith(('http://', 'https://')):
            conn.execute(sa.text("UPDATE update_result SET git_provider = :p WHERE id = :i"),
                         {'p': detect_provider(sources), 'i': rid})


def downgrade():
    for table in list(_TABLES) + ['importer_result', 'update_result']:
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_index(f'ix_{table}_git_provider')
            batch_op.drop_column('git_provider')
