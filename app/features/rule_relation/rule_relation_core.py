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


# Relation types meaning "the source rule NEEDS the target rule to work" —
# YARA condition references, Wazuh if_* parents, Kunai rule() composition,
# and the manual "depends on".
DEPENDENCY_RELATION_TYPES = ('yara_condition_ref', 'depends_on', 'if_sid', 'if_matched_sid',
                             'if_group', 'if_matched_group', 'rule_ref')
DEPENDENCY_GRAPH_MAX_NODES = 300


def get_dependency_graph(rule_id: int, max_nodes: int = DEPENDENCY_GRAPH_MAX_NODES) -> dict:
    """Every rule this one needs (and what those need, transitively) and
    every rule that needs it (transitively), as a graph:

        nodes: [{id, uuid, title, format, role: self|requires|required_by, depth, via}]
        edges: [{from, to, type}]   # from NEEDS to

    `via` is the node through which a rule was first reached — enough to
    draw the chains as an indented tree. Breadth-first in each direction,
    stopped at max_nodes (truncated=True)."""
    root = Rule.query.get(rule_id)
    nodes = {rule_id: {"id": rule_id, "uuid": root.uuid, "title": root.title, "format": root.format,
                       "role": "self", "depth": 0, "via": None}}
    edges = {}
    truncated = False

    def walk(role, follow_outgoing):
        nonlocal truncated
        frontier, depth = [rule_id], 0
        while frontier and not truncated:
            depth += 1
            col = RuleRelation.source_rule_id if follow_outgoing else RuleRelation.target_rule_id
            rels = (RuleRelation.query
                    .filter(col.in_(frontier), RuleRelation.relation_type.in_(DEPENDENCY_RELATION_TYPES))
                    .all())
            nxt = []
            for rel in rels:
                here, other = ((rel.source_rule_id, rel.target_rule_id) if follow_outgoing
                               else (rel.target_rule_id, rel.source_rule_id))
                other_rule = rel.target_rule if follow_outgoing else rel.source_rule
                if other_rule is None or other_rule.is_deleted:
                    continue
                if other not in nodes:
                    if len(nodes) >= max_nodes:
                        truncated = True
                        break
                    nodes[other] = {"id": other, "uuid": other_rule.uuid, "title": other_rule.title,
                                    "format": other_rule.format, "role": role, "depth": depth, "via": here}
                    nxt.append(other)
                edges[(rel.source_rule_id, rel.target_rule_id)] = rel.relation_type
            frontier = nxt

    walk("requires", True)
    walk("required_by", False)
    return {
        "nodes": list(nodes.values()),
        "edges": [{"from": a, "to": b, "type": t} for (a, b), t in edges.items() if a in nodes and b in nodes],
        "requires_count": sum(1 for n in nodes.values() if n["role"] == "requires"),
        "required_by_count": sum(1 for n in nodes.values() if n["role"] == "required_by"),
        "truncated": truncated,
    }


def _safe_file_part(text: str, fallback: str = "rule") -> str:
    import re
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", (text or "").strip()).strip("._")
    return clean[:80] or fallback


def dependency_install_order(rule_ids: list, edges: list) -> list:
    """rule_ids sorted so that every rule comes after the rules it needs
    (edges: [{from, to}] — `from` needs `to`); what a YARA file declaring
    them all has to follow. Rules caught in a cycle keep their given order
    at the end."""
    wanted = set(rule_ids)
    needs = {rid: set() for rid in rule_ids}
    for e in edges:
        if e["from"] in wanted and e["to"] in wanted and e["from"] != e["to"]:
            needs[e["from"]].add(e["to"])
    order, done = [], set()
    remaining = list(rule_ids)
    while remaining:
        ready = [rid for rid in remaining if needs[rid] <= done]
        if not ready:
            order += remaining
            break
        for rid in ready:
            order.append(rid)
            done.add(rid)
        remaining = [rid for rid in remaining if rid not in done]
    return order


def build_dependency_zip(rule_id: int, include_needed_by: bool = False):
    """(BytesIO, filename, rule_count) — the rule and every rule it needs
    (transitively), one file each in the same folder, plus a README with
    the chain and, when they're all YARA, one combined .yar declaring them
    in the order they compile. include_needed_by adds the rules that need
    this one."""
    import io
    import zipfile

    graph = get_dependency_graph(rule_id)
    roles = {"self", "requires"} | ({"required_by"} if include_needed_by else set())
    picked = [n for n in graph["nodes"] if n["role"] in roles]
    rules = {r.id: r for r in Rule.query.filter(Rule.id.in_([n["id"] for n in picked]),
                                                Rule.is_deleted == False)}
    order = dependency_install_order([n["id"] for n in picked if n["id"] in rules], graph["edges"])
    root = rules[rule_id]
    folder = f"{_safe_file_part(root.title)}_with_dependencies"
    role_of = {n["id"]: n for n in picked}

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        used = set()
        lines = [f"# {root.title} — with its dependencies", "",
                 f"Rule {root.uuid} ({root.format}) and the {len(order) - 1} rule(s) it comes with, "
                 "listed in the order they have to be loaded (a rule after the rules it needs).", "",
                 "| # | Rule | Format | Role | File |", "|---|---|---|---|---|"]
        for i, rid in enumerate(order, 1):
            r = rules[rid]
            name = f"{_safe_file_part(r.title)}_{r.id}.{r.get_extension()}"
            while name in used:
                name = f"{r.id}_{name}"
            used.add(name)
            zf.writestr(f"{folder}/{name}", r.to_string or "")
            node = role_of[rid]
            role = {"self": "this rule", "requires": f"needed (level {node['depth']})",
                    "required_by": f"needs it (level {node['depth']})"}[node["role"]]
            lines.append(f"| {i} | {r.title.replace('|', '/')} | {r.format} | {role} | `{name}` |")

        if all((rules[rid].format or "").lower() == "yara" for rid in order) and len(order) > 1:
            combined = "\n\n".join(f"// ── {rules[rid].title} (rule {rules[rid].uuid})\n{rules[rid].to_string or ''}"
                                    for rid in order)
            combined_name = f"{_safe_file_part(root.title)}_combined.yar"
            zf.writestr(f"{folder}/{combined_name}", combined + "\n")
            lines += ["", f"`{combined_name}` declares them all in that order — load it on its own."]

        zf.writestr(f"{folder}/README.md", "\n".join(lines) + "\n")
    buf.seek(0)
    return buf, f"{folder}.zip", len(order)


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
