"""
rule_relation_core.py — Business logic for rule-to-rule relationships.

A curated, typed, directional edge between two rules (e.g. a Wazuh rule's
<if_sid> pointing at another rule, two Kunai rules sharing a correlation
hash, or a user manually noting one rule is a variant of another). This is
NOT the RuleSimilarity/SimilarResult system (app/features/rule/utils/
similar_rules/) — that's a corpus-wide TF-IDF/FAISS content-similarity
scan with no semantics beyond a fuzzy score. Both systems coexist.

Key functions:
  - add_relation(source_rule_id, target_rule_id, relation_type, ...) -> (RuleRelation | None, status)
  - remove_relation(relation_uuid) -> bool
  - get_relations_for_rule(rule_id) -> {'outgoing': [...], 'incoming': [...]}
  - count_relations_for_rule(rule_id) -> int
  - get_relations_page(rule_id, direction, page, per_page) -> paginated dict
"""
import uuid as uuid_mod
import datetime
import json

from sqlalchemy import func

from ... import db
from ...core.db_class.db import Rule, RuleRelation, RULE_RELATION_TYPES

# Cap on how many outgoing links a user can hand-create for one rule from
# the UI (the create/edit-page picker) — keeps a rule's "Linked Rules" page
# from becoming an unreadable wall of links and discourages using this as a
# bulk-tagging mechanism. Deliberately NOT enforced for source='auto' links
# (Wazuh if_sid/if_group, Kunai rule() composition, ...) — those are
# extracted from the rule's own real structure during import, so a widely-
# depended-on base rule legitimately ending up with hundreds of incoming
# auto links is expected, not abuse.
MAX_MANUAL_RELATIONS_PER_RULE = 20


def add_relation(source_rule_id: int, target_rule_id: int, relation_type: str,
                  note: str = None, user_id: int = None, source: str = 'manual'):
    """Returns (RuleRelation | None, status) where status is one of
    'source_not_found' | 'target_not_found' | 'invalid_relation_type' |
    'self_link_rejected' | 'already_exists' | 'limit_reached' | 'created'."""
    if source_rule_id == target_rule_id:
        return None, 'self_link_rejected'

    if source == 'manual' and relation_type not in RULE_RELATION_TYPES:
        return None, 'invalid_relation_type'

    src = Rule.query.get(source_rule_id)
    if not src or src.is_deleted:
        return None, 'source_not_found'

    tgt = Rule.query.get(target_rule_id)
    if not tgt or tgt.is_deleted:
        return None, 'target_not_found'

    existing = RuleRelation.query.filter_by(
        source_rule_id=source_rule_id, target_rule_id=target_rule_id, relation_type=relation_type
    ).first()
    if existing:
        return existing, 'already_exists'

    if source == 'manual':
        current_count = RuleRelation.query.filter_by(source_rule_id=source_rule_id, source='manual').count()
        if current_count >= MAX_MANUAL_RELATIONS_PER_RULE:
            return None, 'limit_reached'

    relation = RuleRelation(
        uuid=str(uuid_mod.uuid4()),
        source_rule_id=source_rule_id,
        target_rule_id=target_rule_id,
        relation_type=relation_type,
        note=(note or '').strip()[:255] or None,
        user_id=user_id,
        source=source,
        added_at=datetime.datetime.now(tz=datetime.timezone.utc),
    )
    db.session.add(relation)
    db.session.commit()
    _refresh_rule_quality_score(source_rule_id)
    return relation, 'created'


def sync_manual_relations(rule_id: int, related_rules_input, user_id: int = None) -> None:
    """Reconciles a rule's manual outgoing relations to match
    related_rules_input exactly — one diff-and-apply, not one API call per
    pick/unpick. Used by the edit-rule form's Save button: the Linked Rules
    picker there only updates its own local modelValue while the user is
    editing (same deferred pattern as Tags), so nothing is actually written
    until this runs. Never touches source='auto' links (Wazuh if_sid, Kunai
    rule() composition, ...) — those aren't part of this picker's domain.

    related_rules_input is either a JSON string or an already-parsed list of
    {id, relation_type} dicts (extra keys, e.g. title/format for display,
    are ignored).
    """
    try:
        data_list = json.loads(related_rules_input) if isinstance(related_rules_input, str) else (related_rules_input or [])
    except (ValueError, TypeError):
        data_list = []
    if not isinstance(data_list, list):
        data_list = []

    new_related = {}
    for r in data_list:
        if isinstance(r, dict) and r.get('id'):
            try:
                new_related[int(r['id'])] = r.get('relation_type') or 'references'
            except (TypeError, ValueError):
                pass

    current = RuleRelation.query.filter_by(source_rule_id=rule_id, source='manual').all()
    current_by_target = {a.target_rule_id: a.relation_type for a in current}

    # relation_type is part of the uniqueness key, not an in-place field —
    # a type change is a remove + re-add, same as an outright unlink.
    for assoc in current:
        if new_related.get(assoc.target_rule_id) != assoc.relation_type:
            db.session.delete(assoc)
    db.session.commit()

    for target_id, relation_type in new_related.items():
        if current_by_target.get(target_id) != relation_type:
            add_relation(rule_id, target_id, relation_type, user_id=user_id, source='manual')


def remove_relation(relation_uuid: str) -> bool:
    relation = RuleRelation.query.filter_by(uuid=relation_uuid).first()
    if not relation:
        return False
    rule_id = relation.source_rule_id
    db.session.delete(relation)
    db.session.commit()
    _refresh_rule_quality_score(rule_id)
    return True


def get_relation_by_uuid(relation_uuid: str) -> RuleRelation:
    return RuleRelation.query.filter_by(uuid=relation_uuid).first()


def get_relations_for_rule(rule_id: int) -> dict:
    """{'outgoing': [...], 'incoming': [...]} — unpaginated, used by the
    create/edit-page picker (preloading a rule's own links, bounded by
    MAX_MANUAL_RELATIONS_PER_RULE on the outgoing side) and by
    count_relations_for_rule below. NOT used by the dedicated Linked Rules
    page — an incoming count can be large for a widely-depended-on base
    rule (auto links aren't capped), so that page calls
    get_relations_page instead. Relations where the other side's rule has
    been hard-deleted can't exist (ondelete=CASCADE), but a soft-deleted
    other side is filtered out here rather than in the DB, same as tags/
    ATT&CK/bundles leave the row in place and let the read path hide it."""
    outgoing = (
        RuleRelation.query.filter_by(source_rule_id=rule_id)
        .order_by(RuleRelation.added_at.desc())
        .all()
    )
    incoming = (
        RuleRelation.query.filter_by(target_rule_id=rule_id)
        .order_by(RuleRelation.added_at.desc())
        .all()
    )
    return {
        'outgoing': [r.to_json('outgoing') for r in outgoing if r.target_rule and not r.target_rule.is_deleted],
        'incoming': [r.to_json('incoming') for r in incoming if r.source_rule and not r.source_rule.is_deleted],
    }


def count_relations_for_rule(rule_id: int) -> int:
    """outgoing + incoming, both directions — drives the detail page's
    'Linked Rules' nav tab (only shown when > 0, see
    macros/detail_rule_nav.html) without paying for the full join/filter
    get_relations_for_rule does. Deliberately does NOT filter out a
    soft-deleted other side (a plain count doesn't need to), so this can
    occasionally read slightly high for a moment right after the other
    side of a link gets soft-deleted — negligible for a nav badge."""
    return (
        RuleRelation.query.filter_by(source_rule_id=rule_id).count()
        + RuleRelation.query.filter_by(target_rule_id=rule_id).count()
    )


def count_relations_for_rules_batch(rule_ids: list) -> dict:
    """{rule_id: outgoing+incoming relation count} for every id in rule_ids —
    two GROUP BY queries total, not one COUNT per rule. Same batching
    pattern as get_tags_for_rules_batch/attacks_by_rule in
    serialize_rules_for_data_table, which is what feeds this: RuleList's
    optional 'N linked rules' badge (showRelatedCount)."""
    if not rule_ids:
        return {}
    counts = {}
    for rid, cnt in (db.session.query(RuleRelation.source_rule_id, func.count(RuleRelation.id))
                      .filter(RuleRelation.source_rule_id.in_(rule_ids))
                      .group_by(RuleRelation.source_rule_id).all()):
        counts[rid] = counts.get(rid, 0) + cnt
    for rid, cnt in (db.session.query(RuleRelation.target_rule_id, func.count(RuleRelation.id))
                      .filter(RuleRelation.target_rule_id.in_(rule_ids))
                      .group_by(RuleRelation.target_rule_id).all()):
        counts[rid] = counts.get(rid, 0) + cnt
    return counts


def get_relations_page(rule_id: int, direction: str, page: int = 1, per_page: int = 20) -> dict:
    """Paginated version of one direction of get_relations_for_rule — for
    the dedicated Linked Rules page, where an incoming count can be large
    (auto-detected links aren't capped). direction is 'outgoing' or
    'incoming'."""
    if direction == 'incoming':
        query = (
            RuleRelation.query
            .join(Rule, RuleRelation.source_rule_id == Rule.id)
            .filter(RuleRelation.target_rule_id == rule_id, Rule.is_deleted == False)
        )
    else:
        query = (
            RuleRelation.query
            .join(Rule, RuleRelation.target_rule_id == Rule.id)
            .filter(RuleRelation.source_rule_id == rule_id, Rule.is_deleted == False)
        )

    query = query.order_by(RuleRelation.added_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        'items': [r.to_json(direction) for r in pagination.items],
        'total': pagination.total,
        'total_pages': pagination.pages,
        'current_page': pagination.page,
    }


def resolve_and_link_relations(rule_instance, raw_text: str, metadata: dict, new_rule,
                                correlation_seen: dict, lock=None) -> None:
    """Shared by every import entry point (GitHub import's session_class.py,
    the direct-repo Process_rules_by_format, and the sync-schedule update
    path) — calls the format's optional extract_relations() (empty by
    default — see RuleType.extract_relations) and turns whatever it
    reports into RuleRelation rows, so each pipeline only needs to own its
    own correlation_seen dict + lock lifecycle (matching its own batch/
    threading shape) rather than reimplementing the resolution logic.

      - 'target_ref' (e.g. Wazuh if_sid): resolved against the live DB
        (same format+source, active only). A reference that can't resolve
        yet (target not in the DB, not yet processed this batch either) is
        silently skipped and self-heals the next time this rule is
        re-synced, once the target exists.
      - 'correlation_key' (e.g. Kunai's shared hash): only correlates
        rules seen within `correlation_seen` — typically scoped to a
        single import run. A rule from an earlier run sharing the same key
        isn't retroactively linked; that would need searching existing
        RuleRelation.note values, not implemented here.

    `lock` guards `correlation_seen` for a multi-threaded caller (pass a
    threading.Lock already used for that dict); a single-threaded caller
    can omit it.
    """
    try:
        relations = rule_instance.extract_relations(raw_text, metadata)
    except Exception:
        return
    if not relations:
        return

    fmt = metadata.get('format')
    source = metadata.get('source')

    for rel in relations:
        if rel.get('kind') == 'target_ref':
            target_identifier = rel.get('target_identifier')
            relation_type = rel.get('relation_type', 'references')
            if not target_identifier:
                continue
            target = (
                Rule.query.filter_by(format=fmt, source=source, original_uuid=target_identifier, is_deleted=False)
                .first()
            )
            if target and target.id != new_rule.id:
                add_relation(new_rule.id, target.id, relation_type, note=target_identifier,
                             user_id=None, source='auto')

        elif rel.get('kind') == 'correlation_key':
            key = rel.get('key')
            relation_type = rel.get('relation_type', 'related')
            if not key:
                continue
            dict_key = (fmt, key)

            def _link_to_peers():
                peers = correlation_seen.setdefault(dict_key, [])
                existing_peers = list(peers)
                peers.append(new_rule.id)
                return existing_peers

            existing_peers = _link_to_peers() if lock is None else _with_lock(lock, _link_to_peers)
            for peer_id in existing_peers:
                add_relation(peer_id, new_rule.id, relation_type, note=key, user_id=None, source='auto')


def _with_lock(lock, fn):
    with lock:
        return fn()


def _refresh_rule_quality_score(rule_id: int) -> None:
    """Same fire-and-forget refresh hook as attack_core.py's — a rule
    linking to related rules is a documentation-completeness signal like
    ATT&CK mapping, so this needs a full recompute, not just an
    engagement-boost-only refresh."""
    try:
        from app.features.rule.rule_quality.quality_score_core import recompute_rule_quality_score
        rule = Rule.query.get(rule_id)
        if rule:
            recompute_rule_quality_score(rule)
    except Exception:
        pass
