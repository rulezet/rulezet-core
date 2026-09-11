"""add multi-repo support to rule_mirror_config

Revision ID: a76fb80f2123
Revises: 5ca6827b9111
Create Date: 2026-09-11 14:30:02.370545

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a76fb80f2123'
down_revision = '5ca6827b9111'
branch_labels = None
depends_on = None


# NOTE: autogenerate also proposed dropping/recreating all 8 pg_trgm GIN
# indexes on `rule` — a known false positive (see 5ca6827b9111), since
# those were created via raw op.execute() and aren't visible to
# SQLAlchemy's model-based diffing. Stripped from this migration; do not
# reintroduce them.

def upgrade():
    with op.batch_alter_table('rule_mirror_config', schema=None) as batch_op:
        batch_op.add_column(sa.Column('uuid', sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column('name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(), nullable=True))

    # Backfill existing row(s) from the previous single-config design
    # before tightening uuid/name to NOT NULL + unique.
    conn = op.get_bind()
    rows = conn.execute(sa.text('SELECT id FROM rule_mirror_config WHERE uuid IS NULL')).fetchall()
    for (row_id,) in rows:
        conn.execute(
            sa.text('UPDATE rule_mirror_config SET uuid = :uuid, name = :name WHERE id = :id'),
            {'uuid': str(__import__('uuid').uuid4()), 'name': 'Rulesets mirror', 'id': row_id},
        )

    with op.batch_alter_table('rule_mirror_config', schema=None) as batch_op:
        batch_op.alter_column('uuid', nullable=False)
        batch_op.alter_column('name', nullable=False)
        batch_op.create_unique_constraint('uq_rule_mirror_config_uuid', ['uuid'])


def downgrade():
    with op.batch_alter_table('rule_mirror_config', schema=None) as batch_op:
        batch_op.drop_constraint('uq_rule_mirror_config_uuid', type_='unique')
        batch_op.drop_column('created_at')
        batch_op.drop_column('name')
        batch_op.drop_column('uuid')
