"""
bundle_ai_core.py — the material the Bundle Analysis agent reasons over.

build_bundle_context() turns everything Rulezet knows about a bundle into
one size-bounded text digest: identity, composition, a per-rule digest,
folder structure, ATT&CK coverage, health checks, community notes, releases
and README-type documents. Runs inside the background job worker — no
request context, so no current_user: only PUBLIC tags are ever included
(the resulting report can be made public, it must not leak private tags).

Budgets are in characters (≈ 3.5 chars/token): the digest stays around
10k chars (~3k tokens). On CPU-only Ollama the model reads ~5 tokens/s, so
every extra kilobyte here is ~1 minute of waiting — and the prompt, the
digest and the whole section-by-section review must fit in 8k tokens.
"""
import json
from collections import Counter

from app import db
from app.core.db_class.db import (
    AttackTechnique, Bundle, BundleNode, BundleNote, BundleRelease, BundleRuleAssociation,
    BundleTagAssociation, Rule, RuleAttackAssociation, RuleTagAssociation, Tag, User,
)

RULE_DIGEST_CHARS = 4500
STRUCTURE_CHARS   = 900
DOCS_CHARS        = 1500
SAMPLES_CHARS     = 800
NOTES_CHARS       = 800
DESC_CHARS        = 900


def _clip(text, n):
    text = (text or '').strip()
    return text if len(text) <= n else text[:n].rstrip() + '…'


def _one_line(text, n):
    return _clip(' '.join((text or '').split()), n)


def _public_tag_names_by_rule(rule_ids):
    out = {}
    if not rule_ids:
        return out
    rows = (db.session.query(RuleTagAssociation.rule_id, Tag.name)
            .join(Tag, RuleTagAssociation.tag_id == Tag.id)
            .filter(RuleTagAssociation.rule_id.in_(rule_ids), Tag.is_active == True,
                    Tag.visibility.ilike('public'))
            .all())
    for rid, name in rows:
        out.setdefault(rid, []).append(name)
    return out


def _attacks_by_rule(rule_ids):
    out = {}
    if not rule_ids:
        return out
    rows = (db.session.query(RuleAttackAssociation.rule_id, AttackTechnique.technique_id, AttackTechnique.name)
            .join(AttackTechnique, RuleAttackAssociation.technique_id == AttackTechnique.technique_id)
            .filter(RuleAttackAssociation.rule_id.in_(rule_ids)).all())
    for rid, tid, name in rows:
        out.setdefault(rid, []).append(f"{tid} {name}")
    return out


def _cves(raw):
    try:
        v = json.loads(raw) if raw else []
        return [c for c in v if isinstance(c, str) and c.strip()] if isinstance(v, list) else []
    except (ValueError, TypeError):
        return []


def _tree_paths(bundle_id):
    """(folder_file_counts {folder_path: n_files}, rule_path_by_id, doc_nodes)."""
    nodes = (db.session.query(BundleNode.id, BundleNode.parent_id, BundleNode.name, BundleNode.node_type,
                              BundleNode.rule_id, BundleNode.custom_content)
             .filter(BundleNode.bundle_id == bundle_id).all())
    by_id = {n.id: n for n in nodes}

    def path_of(n):
        parts, cur, seen = [], n, set()
        while cur is not None and cur.id not in seen:
            seen.add(cur.id)
            parts.append(cur.name)
            cur = by_id.get(cur.parent_id) if cur.parent_id else None
        return '/'.join(reversed(parts))

    folder_counts = Counter()
    rule_paths, docs = {}, []
    for n in nodes:
        if n.node_type == 'folder':
            folder_counts.setdefault(path_of(n), 0)
            continue
        parent = by_id.get(n.parent_id) if n.parent_id else None
        folder_counts[path_of(parent) if parent else '(root)'] += 1
        if n.rule_id:
            rule_paths.setdefault(n.rule_id, path_of(n))
        elif n.custom_content:
            docs.append((path_of(n), n.custom_content))
    return folder_counts, rule_paths, docs


def build_bundle_context(bundle_id):
    """Returns (context_text, snapshot_stats) or (None, None) if the bundle
    doesn't exist. snapshot_stats is stored with the report (meta) so the UI
    can show what the analysis was based on."""
    bundle = db.session.get(Bundle, bundle_id)
    if not bundle:
        return None, None

    owner = db.session.get(User, bundle.user_id)
    rules = (db.session.query(Rule)
             .join(BundleRuleAssociation, BundleRuleAssociation.rule_id == Rule.id)
             .filter(BundleRuleAssociation.bundle_id == bundle_id, Rule.is_deleted == False)
             .order_by(Rule.title.asc()).all())
    rule_ids = [r.id for r in rules]
    tags_by_rule = _public_tag_names_by_rule(rule_ids)
    attacks_by_rule = _attacks_by_rule(rule_ids)
    folder_counts, rule_paths, docs = _tree_paths(bundle_id)

    bundle_tags = [name for (name,) in (
        db.session.query(Tag.name).join(BundleTagAssociation, BundleTagAssociation.tag_id == Tag.id)
        .filter(BundleTagAssociation.bundle_id == bundle_id, Tag.visibility.ilike('public')).all())]
    try:
        vulns = json.loads(bundle.vulnerability_identifiers) if bundle.vulnerability_identifiers else []
    except (ValueError, TypeError):
        vulns = []

    formats = Counter((r.format or 'unknown').lower() for r in rules)
    licenses = Counter((r.license or 'unspecified') for r in rules)
    sources = Counter(_one_line(r.source, 60) or 'unspecified' for r in rules)
    authors = Counter(_one_line(r.author, 40) or 'unknown' for r in rules)
    statuses = Counter((r.status or 'unknown') for r in rules)
    scores = [r.quality_score for r in rules if r.quality_score is not None]
    tag_counter = Counter(t for tl in tags_by_rule.values() for t in tl)
    no_desc = sum(1 for r in rules if not (r.description or '').strip())
    no_attack = sum(1 for r in rules if r.id not in attacks_by_rule)
    with_cve = sum(1 for r in rules if _cves(r.cve_id))
    unplaced = sum(1 for r in rules if r.id not in rule_paths)

    out = []

    # ── Identity ──
    out += [
        "# BUNDLE",
        f"Name: {bundle.name}",
        f"Curated by: {owner.first_name + ' ' + owner.last_name if owner else 'unknown'}"
        f"{' (verified bundle)' if bundle.is_verified else ''}",
        f"Visibility: {'public' if bundle.access else 'private'}",
        f"Created: {bundle.created_at:%Y-%m-%d} · last updated: {bundle.updated_at:%Y-%m-%d}"
        if bundle.created_at and bundle.updated_at else "Dates: unknown",
        f"Community signals: {bundle.vote_up or 0} upvotes, {bundle.vote_down or 0} downvotes, "
        f"{bundle.download_count or 0} downloads, {bundle.view_count or 0} views",
        f"Bundle tags: {', '.join(bundle_tags) if bundle_tags else '(none)'}",
        f"Vulnerabilities linked to the bundle: {', '.join(vulns[:30]) if vulns else '(none)'}",
        "Description:",
        _clip(bundle.description, DESC_CHARS) or "(no description provided)",
        "",
    ]

    # ── Composition ──
    def _top(counter, n=8):
        return ', '.join(f"{k} ({v})" for k, v in counter.most_common(n)) or '(none)'

    out += [
        "# COMPOSITION",
        f"Active rules: {len(rules)}",
        f"Formats: {_top(formats)}",
        f"Lifecycle status: {_top(statuses)}",
        f"Licenses: {_top(licenses, 6)}",
        f"Sources: {_top(sources, 6)}",
        f"Rule authors: {_top(authors, 6)} ({len(authors)} distinct)",
        f"Quality score (0-100): "
        + (f"average {sum(scores) / len(scores):.0f}, min {min(scores):.0f}, max {max(scores):.0f} "
           f"over {len(scores)} scored rules" if scores else "not computed"),
        f"Rules without a description: {no_desc} · without an ATT&CK mapping: {no_attack} · "
        f"linked to a CVE: {with_cve} · not placed in the folder structure: {unplaced}",
        f"Most common rule tags: {_top(tag_counter, 12)}",
        "",
    ]

    # ── ATT&CK coverage ──
    try:
        from .bundle_core import get_attack_coverage
        cov = get_attack_coverage(bundle_id) or {}
    except Exception:
        cov = {}
    if cov.get('tactics'):
        st = cov.get('stats') or {}
        out.append("# MITRE ATT&CK COVERAGE")
        out.append(f"{st.get('covered_tactics', 0)}/{st.get('total_tactics', 0)} tactics covered, "
                   f"{st.get('unique_techniques', 0)} distinct techniques, "
                   f"{st.get('rules_with_attack', 0)}/{st.get('total_rules', len(rules))} rules mapped")
        for t in cov['tactics']:
            if t.get('covered'):
                techs = ', '.join(f"{x['id']}×{x['count']}" for x in t['techniques'][:10])
                more = f" (+{len(t['techniques']) - 10} more)" if len(t['techniques']) > 10 else ''
                out.append(f"- {t['label']}: {t['rule_count']} rule mappings — {techs}{more}")
            else:
                out.append(f"- {t['label']}: NOT covered")
        out.append("")

    # ── Health checks ──
    health = None
    try:
        from .bundle_health_core import bundle_health
        health = bundle_health(bundle_id)
    except Exception as e:
        out += ["# HEALTH CHECKS", f"(health check unavailable: {e})", ""]
    if health:
        out.append("# HEALTH CHECKS (automatic pre-deployment checks)")
        out.append(f"Score: {health.get('score')}/100 · verdict: {health.get('verdict')} · "
                   f"{health['counts'].get('error', 0)} errors, {health['counts'].get('warning', 0)} warnings")
        for c in health.get('checks', []):
            if c.get('level') == 'ok':
                out.append(f"- [ok] {c['title']}")
                continue
            examples = '; '.join(_one_line(f"{i.get('name') or i.get('title') or ''} {i.get('detail') or ''}", 100)
                                 for i in (c.get('items') or [])[:2])
            out.append(f"- [{c['level']}] {c['title']}: {_one_line(c['message'], 170)}"
                       + (f" — e.g. {examples}" if examples else ''))
        out.append("")

    # ── Structure ──
    out.append("# FOLDER STRUCTURE (folder path → files directly inside)")
    lines, used = [], 0
    for path, n in sorted(folder_counts.items()):
        line = f"- {path}: {n}"
        if used + len(line) > STRUCTURE_CHARS:
            lines.append(f"- … {len(folder_counts) - len(lines)} more folders")
            break
        lines.append(line)
        used += len(line)
    out += (lines or ["(no folder structure — rules are only attached, not organised)"]) + [""]

    # ── Documents ──
    if docs:
        docs.sort(key=lambda d: (0 if 'readme' in d[0].lower() else 1, d[0]))
        out.append("# DOCUMENTS SHIPPED WITH THE BUNDLE")
        budget = DOCS_CHARS
        for path, content in docs:
            if budget <= 200:
                out.append(f"(+ other documents not shown: {', '.join(p for p, _ in docs[docs.index((path, content)):][:10])})")
                break
            chunk = _clip(content, min(1100, budget))
            out += [f"## {path}", chunk]
            budget -= len(chunk)
        out.append("")

    # ── Community notes ──
    notes = (BundleNote.query.filter_by(bundle_id=bundle_id)
             .order_by(BundleNote.created_at.desc()).limit(15).all())
    if notes:
        out.append("# COMMUNITY NOTES (known issues reported by users)")
        budget = NOTES_CHARS
        for n in notes:
            line = f"- [{n.status}/{n.severity}] {n.title}: {_one_line(n.content, 180)}"
            if budget - len(line) < 0:
                break
            out.append(line)
            budget -= len(line)
        out.append("")

    # ── Releases ──
    releases = (BundleRelease.query.filter_by(bundle_id=bundle_id)
                .order_by(BundleRelease.created_at.desc()).limit(5).all())
    out.append("# RELEASES")
    if releases:
        for r in releases:
            out.append(f"- {r.version} ({r.created_at:%Y-%m-%d}): {r.rule_count} rules, "
                       f"health {r.health_score if r.health_score is not None else 'n/a'}"
                       + (f" — {_one_line(r.notes, 160)}" if r.notes else ''))
    else:
        out.append("(no release published — the bundle is only available as a moving target)")
    out.append("")

    # ── Per-rule digest ──
    out.append(f"# RULES ({len(rules)})")
    used, shown = 0, 0
    for r in rules:
        bits = [f"- [{(r.format or '?').upper()}] {_one_line(r.title, 70)}"]
        if r.description:
            bits.append(f"— {_one_line(r.description, 80)}")
        if r.id in attacks_by_rule:
            bits.append(f"| {', '.join(a.split(' ', 1)[0] for a in attacks_by_rule[r.id][:3])}")
        cves = _cves(r.cve_id)
        if cves:
            bits.append(f"| {', '.join(cves[:2])}")
        if r.id in rule_paths:
            folder = rule_paths[r.id].rsplit('/', 1)[0] if '/' in rule_paths[r.id] else ''
            if folder:
                bits.append(f"| in {_one_line(folder.split('/', 1)[-1], 40)}")
        line = ' '.join(bits)
        if used + len(line) > RULE_DIGEST_CHARS:
            break
        out.append(line)
        used += len(line)
        shown += 1
    if shown < len(rules):
        out.append(f"- … {len(rules) - shown} more rules not listed individually (see composition above)")
    out.append("")

    # ── Samples: a few real rule bodies, one per format ──
    samples, seen_fmt, budget = [], set(), SAMPLES_CHARS
    for r in sorted(rules, key=lambda x: -(x.quality_score or 0)):
        fmt = (r.format or '').lower()
        if fmt in seen_fmt or not r.to_string or budget < 400:
            continue
        seen_fmt.add(fmt)
        body = _clip(r.to_string, min(700, budget))
        samples += [f"## {r.title} ({fmt})", body]
        budget -= len(body)
        if len(seen_fmt) >= 1:
            break
    if samples:
        out += ["# SAMPLE RULE CONTENT (a few representative rules, truncated)"] + samples

    snapshot = {
        'rule_count': len(rules),
        'formats': dict(formats.most_common(8)),
        'health_score': health.get('score') if health else None,
        'health_verdict': health.get('verdict') if health else None,
        'covered_tactics': (cov.get('stats') or {}).get('covered_tactics') if cov else None,
        'total_tactics': (cov.get('stats') or {}).get('total_tactics') if cov else None,
        'open_notes': sum(1 for n in notes if n.status == 'open'),
        'releases': len(releases),
    }
    return '\n'.join(out), snapshot
