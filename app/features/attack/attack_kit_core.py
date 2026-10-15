"""attack_kit_core.py — the ATT&CK technique page (/attack/technique/<id>),
built like the CVE response kit (features/vulnerability): the technique's
details, every rule mapped to it (and to its sub-techniques), coverage per
format with the gaps, charts, a zip, a bundle. Shared logic in
features/rule/kit_core.py; expected formats in app/config/attack_kit.expected_formats.json.
"""
import re

from sqlalchemy import func

from app import db
from app.core.db_class.attack import AttackTechnique, RuleAttackAssociation
from app.core.db_class.rule import Rule
from app.core.utils.app_settings import setting
from app.features.attack.attack_core import _TACTIC_LABELS_GLOBAL
from app.features.rule import kit_core
from app.features.rule.rule_core import _active

EXPECTED_FORMATS = setting('attack_kit.expected_formats')


def get_technique(technique_id: str):
    return AttackTechnique.query.filter_by(technique_id=(technique_id or '').upper()).first()


def technique_ids(tech) -> list:
    """The technique and, for a parent technique, all its sub-techniques —
    a rule mapped to T1003.001 covers T1003 too."""
    ids = [tech.technique_id]
    if not tech.is_subtechnique:
        ids += [t for (t,) in db.session.query(AttackTechnique.technique_id)
                .filter_by(parent_technique_id=tech.technique_id).all()]
    return ids


def rules_for(ids: list) -> list:
    sub = db.session.query(RuleAttackAssociation.rule_id).filter(RuleAttackAssociation.technique_id.in_(ids))
    return _active().filter(Rule.id.in_(sub)).order_by(Rule.creation_date.desc()).all()


def _rule_counts(ids: list) -> dict:
    rows = (db.session.query(RuleAttackAssociation.technique_id, func.count(func.distinct(Rule.id)))
            .join(Rule, Rule.id == RuleAttackAssociation.rule_id)
            .filter(RuleAttackAssociation.technique_id.in_(ids), Rule.is_deleted == False)  # noqa: E712
            .group_by(RuleAttackAssociation.technique_id).all())
    return dict(rows)


_CITATION_RE = re.compile(r'\s*\(Citation:[^)]*\)')
_MD_LINK_RE = re.compile(r'\[([^\]]+)\]\((?:https?://)[^)]*\)')
_CODE_RE = re.compile(r'<code>(.*?)</code>')


def clean_description(text: str | None) -> str | None:
    """MITRE's STIX descriptions carry Markdown links, (Citation: …)
    markers and <code> tags — plain readable text for the page."""
    if not text:
        return text
    text = _CITATION_RE.sub('', text)
    text = _MD_LINK_RE.sub(r'\1', text)
    text = _CODE_RE.sub(r'\1', text)
    return re.sub(r'[ \t]+', ' ', text).strip()


def build_kit(tech) -> dict:
    ids = technique_ids(tech)
    rules = rules_for(ids)
    coverage = kit_core.format_coverage(rules, EXPECTED_FORMATS)
    counts = _rule_counts(ids)

    subs = [t for t in AttackTechnique.query.filter(AttackTechnique.technique_id.in_(ids[1:]))
            .order_by(AttackTechnique.technique_id).all()] if len(ids) > 1 else []
    parent = get_technique(tech.parent_technique_id) if tech.parent_technique_id else None
    siblings = []
    if parent:
        siblings = [{'id': t.technique_id, 'name': t.name}
                    for t in AttackTechnique.query.filter_by(parent_technique_id=parent.technique_id)
                    .order_by(AttackTechnique.technique_id).all() if t.technique_id != tech.technique_id]

    from app.core.db_class.bundle import Bundle, BundleRuleAssociation
    rule_ids = [r.id for r in rules]
    bundles = []
    if rule_ids:
        rows = (db.session.query(Bundle, func.count(BundleRuleAssociation.id))
                .join(BundleRuleAssociation, BundleRuleAssociation.bundle_id == Bundle.id)
                .filter(BundleRuleAssociation.rule_id.in_(rule_ids), Bundle.access == True)  # noqa: E712
                .group_by(Bundle.id).order_by(func.count(BundleRuleAssociation.id).desc()).limit(10).all())
        bundles = [{'id': b.id, 'uuid': b.uuid, 'name': b.name, 'rule_count': n} for b, n in rows]

    return {
        'id': tech.technique_id,
        'ids': ids,
        'info': {
            'name': tech.name,
            'description': clean_description(tech.description),
            'url': tech.url or f"https://attack.mitre.org/techniques/{tech.technique_id.replace('.', '/')}/",
            'deprecated': bool(tech.deprecated),
            'is_subtechnique': bool(tech.is_subtechnique),
            'tactics': [{'key': k, 'label': _TACTIC_LABELS_GLOBAL.get(k, k.replace('-', ' ').title())}
                        for k in (tech.tactic_keys or [])],
            'parent': {'id': parent.technique_id, 'name': parent.name} if parent else None,
            'siblings': siblings,
            'subtechniques': [{'id': t.technique_id, 'name': t.name, 'rules': counts.get(t.technique_id, 0)} for t in subs],
            'own_rules': counts.get(tech.technique_id, 0),
        },
        'total_rules': len(rules),
        'formats': coverage['formats'],
        'covered_formats': coverage['covered_formats'],
        'gaps': coverage['gaps'],
        'covered_expected': coverage['covered_expected'],
        'expected_total': coverage['expected_total'],
        'bundles': bundles,
    }


def build_stats(tech) -> dict:
    """Chart data for the Coverage card — computed only when it's opened."""
    return kit_core.format_coverage(rules_for(technique_ids(tech)), EXPECTED_FORMATS, with_stats=True)['stats']


def ai_draft_prompt(tech) -> str:
    parts = [f'Detect {tech.technique_id} {tech.name} (MITRE ATT&CK).']
    if tech.description:
        parts.append(tech.description[:1200])
    return ' '.join(parts)[:1800]


def build_zip(tech):
    kit = build_kit(tech)
    rules = rules_for(kit['ids'])
    lines = [f"{tech.technique_id} {tech.name}", '',
             f"{len(rules)} rule(s): " + ', '.join(f"{f['format']} ({f['count']})" for f in kit['formats'] if f['count']),
             f"Missing formats: {', '.join(kit['gaps']) or 'none'}",
             f"Details: {kit['info']['url']}"]
    return kit_core.zip_rules(rules, f'{tech.technique_id} — Rulezet detection kit', lines), len(rules)


def create_kit_bundle(tech, user):
    rules = rules_for(technique_ids(tech))
    if not rules:
        return None, 'There is no rule for this technique yet.'
    description = (f"Every Rulezet rule mapped to MITRE ATT&CK {tech.technique_id} — {tech.name}"
                   + ('' if tech.is_subtechnique else ' (sub-techniques included)') + '.')
    bundle = kit_core.bundle_from_rules(f'{tech.technique_id} {tech.name}'[:200], description, rules, user)
    return bundle, f'Bundle created with {len(rules)} rule(s).'
