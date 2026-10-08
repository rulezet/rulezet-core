"""tag.namespace (browse folder, kept in sync by an ORM listener) + pg_trgm index on tag.name

The tag pickers and filters used to download every tag (85 MB of JSON for
~75k tags) to group them into folders client-side. With the folder stored
per tag they list and count folders in SQL and load one folder at a time;
the trigram index keeps their substring search (ILIKE '%…%') fast.

Revision ID: d4f2b7e9c1a3
Revises: c3e8a1f5d7b2
Create Date: 2026-09-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4f2b7e9c1a3'
down_revision = 'c3e8a1f5d7b2'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('tag', schema=None) as batch_op:
        batch_op.add_column(sa.Column('namespace', sa.String(length=255), nullable=True))
        batch_op.create_index('ix_tag_namespace', ['namespace'], unique=False)

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        # Same rule as app.core.db_class.db.tag_namespace()
        op.execute("""
            UPDATE tag SET namespace = CASE
                WHEN name LIKE 'misp-galaxy:%%=%%' THEN left(split_part(split_part(name, ':', 2), '=', 1), 255)
                WHEN position(':' in name) > 0      THEN left(split_part(name, ':', 1), 255)
                ELSE ''
            END
        """)
        op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')
        with op.get_context().autocommit_block():
            op.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_tag_name_trgm '
                       'ON tag USING gin (name gin_trgm_ops)')
        op.execute('ANALYZE tag')
    else:
        from app.core.db_class.db import tag_namespace
        rows = bind.execute(sa.text('SELECT id, name FROM tag')).fetchall()
        for tag_id, name in rows:
            bind.execute(sa.text('UPDATE tag SET namespace = :ns WHERE id = :id'),
                         {'ns': tag_namespace(name), 'id': tag_id})


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        with op.get_context().autocommit_block():
            op.execute('DROP INDEX CONCURRENTLY IF EXISTS ix_tag_name_trgm')
    with op.batch_alter_table('tag', schema=None) as batch_op:
        batch_op.drop_index('ix_tag_namespace')
        batch_op.drop_column('namespace')
