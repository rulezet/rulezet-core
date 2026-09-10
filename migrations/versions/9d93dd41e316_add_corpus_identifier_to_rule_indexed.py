"""add corpus_identifier to rule, indexed

Revision ID: 9d93dd41e316
Revises: 653504fe1a0c
Create Date: 2026-09-10 15:13:28.622407

"""
import re

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9d93dd41e316'
down_revision = '653504fe1a0c'
branch_labels = None
depends_on = None


# Frozen copy of rule_core._extract_corpus_identifier() as it stood when this
# migration was written — a migration must not depend on application code
# that's free to change (or disappear) later, so the extraction logic is
# duplicated here rather than imported.
def _extract_corpus_identifier(rule_format, content):
    fmt = (rule_format or '').lower()
    content = content or ''
    if fmt == 'suricata':
        m = re.search(r'\bsid\s*:\s*(\d+)', content, re.IGNORECASE)
        return m.group(1) if m else None
    if fmt == 'yara':
        m = re.search(r'\brule\s+(\w+)', content)
        return m.group(1) if m else None
    if fmt == 'wazuh':
        m = re.search(r'<rule\b[^>]*\bid\s*=\s*"([^"]+)"', content)
        return m.group(1) if m else None
    return None


def _backfill_corpus_identifier():
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id, format, to_string FROM rule "
        "WHERE format IN ('suricata', 'yara', 'wazuh')"
    )).fetchall()

    for rule_id, fmt, to_string in rows:
        identifier = _extract_corpus_identifier(fmt, to_string)
        if identifier:
            bind.execute(
                sa.text("UPDATE rule SET corpus_identifier = :identifier WHERE id = :id"),
                {"identifier": identifier, "id": rule_id},
            )


def upgrade():
    with op.batch_alter_table('rule', schema=None) as batch_op:
        batch_op.add_column(sa.Column('corpus_identifier', sa.String(length=191), nullable=True))

    # Backfill before indexing — cheaper than updating the index incrementally
    # for every one of these rows.
    _backfill_corpus_identifier()

    with op.batch_alter_table('rule', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_rule_corpus_identifier'), ['corpus_identifier'], unique=False)


def downgrade():
    with op.batch_alter_table('rule', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_rule_corpus_identifier'))
        batch_op.drop_column('corpus_identifier')
