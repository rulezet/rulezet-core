"""unified comment_v2 and comment_reaction tables; migrate existing comment data

Revision ID: c7a1f3e2d9b5
Revises: 12036720d06b
Create Date: 2026-06-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import uuid as _uuid_mod

revision = 'c7a1f3e2d9b5'
down_revision = '12036720d06b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'comment_v2',
        sa.Column('id',               sa.Integer,     primary_key=True, autoincrement=True),
        sa.Column('uuid',             sa.String(36),  nullable=False, unique=True),
        sa.Column('content',          sa.Text,        nullable=False),
        sa.Column('content_original', sa.Text,        nullable=True),
        sa.Column('parent_id',        sa.Integer,     sa.ForeignKey('comment_v2.id', ondelete='SET NULL'), nullable=True),
        sa.Column('depth',            sa.Integer,     nullable=False, server_default='0'),
        sa.Column('root_id',          sa.Integer,     nullable=True),
        sa.Column('object_type',      sa.String(64),  nullable=False),
        sa.Column('object_id',        sa.Integer,     nullable=False),
        sa.Column('is_public',        sa.Boolean,     nullable=False, server_default=sa.true()),
        sa.Column('is_active',        sa.Boolean,     nullable=False, server_default=sa.true()),
        sa.Column('deleted_at',       sa.DateTime,    nullable=True),
        sa.Column('deleted_by',       sa.Integer,     nullable=True),
        sa.Column('created_at',       sa.DateTime,    nullable=False),
        sa.Column('updated_at',       sa.DateTime,    nullable=True),
        sa.Column('created_by',       sa.Integer,     sa.ForeignKey('user.id', ondelete='SET NULL'), nullable=True),
    )
    op.create_index('ix_comment_v2_uuid',        'comment_v2', ['uuid'])
    op.create_index('ix_comment_v2_parent_id',   'comment_v2', ['parent_id'])
    op.create_index('ix_comment_v2_root_id',     'comment_v2', ['root_id'])
    op.create_index('ix_comment_v2_object',      'comment_v2', ['object_type', 'object_id'])
    op.create_index('ix_comment_v2_created_by',  'comment_v2', ['created_by'])

    op.create_table(
        'comment_reaction',
        sa.Column('id',         sa.Integer,    primary_key=True, autoincrement=True),
        sa.Column('comment_id', sa.Integer,    sa.ForeignKey('comment_v2.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id',    sa.Integer,    sa.ForeignKey('user.id',       ondelete='CASCADE'), nullable=False),
        sa.Column('reaction',   sa.String(16), nullable=False),
        sa.Column('created_at', sa.DateTime,   nullable=False),
        sa.UniqueConstraint('comment_id', 'user_id', name='uq_comment_reaction_user'),
    )
    op.create_index('ix_comment_reaction_comment_id', 'comment_reaction', ['comment_id'])
    op.create_index('ix_comment_reaction_user_id',    'comment_reaction', ['user_id'])

    # ── Data migration (PostgreSQL only; SQLite test DB has no live data) ─────
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    id_map = {}  # ('rule'|'bundle'|'proposal', old_id) → new_comment_v2_id

    # ── 1. Rule comments (comment → comment_v2, object_type='rule') ──────────
    try:
        rows = bind.execute(text(
            "SELECT id, uuid, rule_id, user_id, content, created_at, updated_at, parent_comment_id "
            "FROM comment ORDER BY id"
        )).fetchall()
    except Exception:
        rows = []

    for row in rows:
        row_uuid = row[1] if row[1] else str(_uuid_mod.uuid4())
        created  = row[5] if row[5] else now
        updated  = row[6] if row[6] else now
        res = bind.execute(text(
            "INSERT INTO comment_v2 "
            "(uuid, content, object_type, object_id, created_by, created_at, updated_at, depth, is_active, is_public) "
            "VALUES (:uuid, :content, 'rule', :oid, :by, :cat, :uat, 0, true, true) RETURNING id"
        ), dict(uuid=row_uuid, content=row[4], oid=row[2], by=row[3], cat=created, uat=updated))
        id_map[('rule', row[0])] = res.fetchone()[0]

    # Fix parent_id for rule comment replies
    for row in rows:
        if row[7]:
            parent_new = id_map.get(('rule', row[7]))
            my_new     = id_map.get(('rule', row[0]))
            if parent_new and my_new:
                bind.execute(text(
                    "UPDATE comment_v2 SET parent_id = :pid, depth = 1, root_id = :rid WHERE id = :id"
                ), dict(pid=parent_new, rid=parent_new, id=my_new))

    # Migrate rule comment reactions (rule_comment_reaction → comment_reaction)
    try:
        rxns = bind.execute(text(
            "SELECT comment_id, user_id, reaction_type, created_at FROM rule_comment_reaction"
        )).fetchall()
        for rxn in rxns:
            new_cid = id_map.get(('rule', rxn[0]))
            if not new_cid:
                continue
            created = rxn[3] if rxn[3] else now
            reaction_val = 'like' if rxn[2] == 'like' else ('dislike' if rxn[2] == 'dislike' else rxn[2][:16])
            try:
                bind.execute(text(
                    "INSERT INTO comment_reaction (comment_id, user_id, reaction, created_at) "
                    "VALUES (:cid, :uid, :r, :cat) "
                    "ON CONFLICT ON CONSTRAINT uq_comment_reaction_user DO NOTHING"
                ), dict(cid=new_cid, uid=rxn[1], r=reaction_val, cat=created))
            except Exception:
                pass
    except Exception:
        pass

    # ── 2. Bundle comments (comment_bundle → comment_v2, object_type='bundle') ─
    try:
        rows_b = bind.execute(text(
            "SELECT id, uuid, bundle_id, user_id, content, created_at, updated_at, parent_comment_id "
            "FROM comment_bundle ORDER BY id"
        )).fetchall()
    except Exception:
        rows_b = []

    for row in rows_b:
        row_uuid = row[1] if row[1] else str(_uuid_mod.uuid4())
        created  = row[5] if row[5] else now
        updated  = row[6] if row[6] else now
        res = bind.execute(text(
            "INSERT INTO comment_v2 "
            "(uuid, content, object_type, object_id, created_by, created_at, updated_at, depth, is_active, is_public) "
            "VALUES (:uuid, :content, 'bundle', :oid, :by, :cat, :uat, 0, true, true) RETURNING id"
        ), dict(uuid=row_uuid, content=row[4], oid=row[2], by=row[3], cat=created, uat=updated))
        id_map[('bundle', row[0])] = res.fetchone()[0]

    for row in rows_b:
        if row[7]:
            parent_new = id_map.get(('bundle', row[7]))
            my_new     = id_map.get(('bundle', row[0]))
            if parent_new and my_new:
                bind.execute(text(
                    "UPDATE comment_v2 SET parent_id = :pid, depth = 1, root_id = :rid WHERE id = :id"
                ), dict(pid=parent_new, rid=parent_new, id=my_new))

    # Migrate bundle reactions (bundle_reaction_comment → comment_reaction)
    try:
        rxns_b = bind.execute(text(
            "SELECT comment_id, user_id, reaction_type, created_at FROM bundle_reaction_comment"
        )).fetchall()
        for rxn in rxns_b:
            new_cid = id_map.get(('bundle', rxn[0]))
            if not new_cid:
                continue
            created = rxn[3] if rxn[3] else now
            reaction_val = 'like' if rxn[2] == 'like' else ('dislike' if rxn[2] == 'dislike' else rxn[2][:16])
            try:
                bind.execute(text(
                    "INSERT INTO comment_reaction (comment_id, user_id, reaction, created_at) "
                    "VALUES (:cid, :uid, :r, :cat) "
                    "ON CONFLICT ON CONSTRAINT uq_comment_reaction_user DO NOTHING"
                ), dict(cid=new_cid, uid=rxn[1], r=reaction_val, cat=created))
            except Exception:
                pass
    except Exception:
        pass

    # ── 3. Proposal comments (rule_edit_comment → comment_v2, object_type='proposal') ─
    try:
        rows_p = bind.execute(text(
            "SELECT id, proposal_id, user_id, content, created_at FROM rule_edit_comment ORDER BY id"
        )).fetchall()
    except Exception:
        rows_p = []

    for row in rows_p:
        created = row[4] if row[4] else now
        res = bind.execute(text(
            "INSERT INTO comment_v2 "
            "(uuid, content, object_type, object_id, created_by, created_at, updated_at, depth, is_active, is_public) "
            "VALUES (:uuid, :content, 'proposal', :oid, :by, :cat, :cat, 0, true, true) RETURNING id"
        ), dict(uuid=str(_uuid_mod.uuid4()), content=row[3], oid=row[1], by=row[2], cat=created))
        id_map[('proposal', row[0])] = res.fetchone()[0]


def downgrade():
    op.drop_table('comment_reaction')
    op.drop_table('comment_v2')
