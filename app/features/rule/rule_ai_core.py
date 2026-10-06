"""
rule_ai_core.py — the material the "In-depth report" rule analysis script
(RuleDeepAnalysisAgent) reasons over. Same idea as
app/features/bundle/bundle_ai_core.py: everything Rulezet actually knows
about one rule, assembled as plain text, each part clipped so the whole
thing fits next to the prompt in the model's context window.

On top of the rule itself (content, metadata, tags) it pulls:
  - the full ATT&CK entries (tactics + description) of the linked techniques;
  - the linked CVEs from Vulnerability Lookup (vulnerability.circl.lu):
    summary, CVSS, CWE, affected products, EPSS, CISA SSVC — only the CVE
    identifier is sent out, never anything about the rule;
  - the quality-score checks that fail, linked rules, bundles shipping it.
"""
import json

from app import db
from app.core.db_class.db import (
    AttackTechnique,
    Bundle,
    BundleRuleAssociation,
    Rule,
    RuleAttackAssociation,
    RuleTagAssociation,
    Tag,
)

CONTENT_CHARS     = 6000
DESC_CHARS        = 1200
TECHNIQUE_CHARS   = 450    # per technique description
MAX_TECHNIQUES    = 6
MAX_CVES          = 4
CVE_SUMMARY_CHARS = 700
CVE_FETCH_TIMEOUT = 8
MAX_RELATIONS     = 8
MAX_BUNDLES       = 6


def _clip(text, limit):
    text = (text or '').strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + ' … (truncated)'


def _parse_cve_ids(raw):
    try:
        ids = json.loads(raw) if raw else []
    except (ValueError, TypeError):
        ids = [raw] if raw else []
    if not isinstance(ids, list):
        ids = []
    seen, out = set(), []
    for c in ids:
        c = str(c or '').strip().upper()
        if c.startswith('CVE-') and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def fetch_cve_details(cve_id):
    """Vulnerability Lookup record for one CVE, normalised by the same parser
    the "blog post from CVE" job uses, plus EPSS. {} if unreachable — the
    report then just says the CVE details were not available."""
    import requests as http_requests
    from app.features.jobs.job_handlers import _parse_circl_v5

    headers = {'Accept': 'application/json', 'User-Agent': 'Rulezet/1.0'}
    parsed = {}
    try:
        resp = http_requests.get(f'https://vulnerability.circl.lu/api/cve/{cve_id.lower()}',
                                 timeout=CVE_FETCH_TIMEOUT, headers=headers)
        raw = resp.json() if resp.ok else None
        if isinstance(raw, dict):
            parsed = _parse_circl_v5(raw)
    except Exception:
        return {}
    if not parsed:
        return {}
    if not parsed.get('cvss_score'):
        # Older CVEs often carry CVSS only in an ADP container (CISA/NVD
        # enrichment), which _parse_circl_v5 doesn't read.
        for adp in ((raw.get('containers') or {}).get('adp') or []):
            for m in (adp.get('metrics') or []) if isinstance(adp, dict) else []:
                for key in ('cvssV3_1', 'cvssV3_0', 'cvssV4_0', 'cvssV2_0'):
                    if isinstance(m, dict) and key in m and m[key].get('baseScore') is not None:
                        parsed['cvss_score']  = str(m[key]['baseScore'])
                        parsed['cvss_vector'] = m[key].get('vectorString', '')
                        parsed['cvss_sev']    = m[key].get('baseSeverity') or ''
                        break
                if parsed.get('cvss_score'):
                    break
            if parsed.get('cvss_score'):
                break
    try:
        resp = http_requests.get(f'https://vulnerability.circl.lu/api/epss/{cve_id}',
                                 timeout=CVE_FETCH_TIMEOUT, headers=headers)
        if resp.ok:
            rows = resp.json().get('data') or []
            score = rows and (rows[0].get('epss') or rows[0].get('score'))
            if score:
                parsed['epss_pct'] = round(float(score) * 100, 2)
    except Exception:
        pass
    return parsed


def _cve_block(cve_id, d):
    if not d:
        return f"- {cve_id}: details not available from Vulnerability Lookup (offline or unknown CVE)."
    lines = [f"- {cve_id}" + (f" — {d['cna_title']}" if d.get('cna_title') else '')]
    if d.get('summary'):
        lines.append(f"  Description: {_clip(d['summary'], CVE_SUMMARY_CHARS)}")
    if d.get('cvss_score'):
        lines.append(f"  CVSS: {d['cvss_score']} ({d.get('cvss_sev') or 'n/a'})"
                     + (f", vector {d['cvss_vector']}" if d.get('cvss_vector') else ''))
    if d.get('epss_pct') is not None:
        lines.append(f"  EPSS (probability of exploitation in the next 30 days): {d['epss_pct']}%")
    if d.get('cwes'):
        lines.append("  Weakness: " + '; '.join(
            name if name.startswith(cid) else f"{cid} {name}".strip() for cid, name in d['cwes'][:3]))
    if d.get('affected'):
        prods = []
        for a in d['affected'][:5]:
            versions = ', '.join(
                (v.get('version') or '') + (f" < {v['lessThan']}" if v.get('lessThan') else '')
                + (f" <= {v['lessThanOrEqual']}" if v.get('lessThanOrEqual') else '')
                for v in (a.get('versions') or [])[:3]
            ).strip(', ')
            prods.append(f"{a.get('vendor') or '?'} {a['product']}" + (f" ({versions})" if versions else ''))
        lines.append("  Affected: " + '; '.join(prods))
    if d.get('ssvc'):
        lines.append("  CISA SSVC: " + ', '.join(f"{k}={v}" for k, v in d['ssvc'].items()))
    if d.get('pub'):
        lines.append(f"  Published: {d['pub']}")
    tagged = [r for r in (d.get('refs') or []) if r.get('tags')]
    if tagged:
        lines.append("  Reference types: " + ', '.join(sorted({t for r in tagged for t in r['tags']}))[:200])
    return '\n'.join(lines)


def build_rule_deep_context(rule_id):
    """(context_text, snapshot) for one rule, or (None, None) if it is gone.
    snapshot is a small dict stored in the generation's meta (what the
    report was grounded on: CVE scores, technique ids…)."""
    rule = db.session.get(Rule, rule_id)
    if not rule or rule.is_deleted:
        return None, None

    tags = [name for (name,) in db.session.query(Tag.name)
            .join(RuleTagAssociation, RuleTagAssociation.tag_id == Tag.id)
            .filter(RuleTagAssociation.rule_id == rule_id).all()]

    techniques = (db.session.query(AttackTechnique)
                  .join(RuleAttackAssociation, RuleAttackAssociation.technique_id == AttackTechnique.technique_id)
                  .filter(RuleAttackAssociation.rule_id == rule_id)
                  .order_by(AttackTechnique.technique_id).all())

    cve_ids = _parse_cve_ids(rule.cve_id)
    cve_details = {c: fetch_cve_details(c) for c in cve_ids[:MAX_CVES]}

    parts = []

    # ── Identity ─────────────────────────────────────────────────────────
    ident = [
        f"Title: {rule.title or '(untitled)'}",
        f"Format: {rule.format or 'unknown'}",
        f"Author: {rule.author or '(unknown)'}",
        f"Source: {rule.source or '(unknown)'}",
        f"License: {rule.license or '(none)'}",
        f"Version: {rule.version or '(none)'}",
    ]
    if rule.creation_date:
        ident.append(f"Created: {rule.creation_date:%Y-%m-%d}")
    if rule.last_modif:
        ident.append(f"Last modified: {rule.last_modif:%Y-%m-%d}")
    if rule.github_path:
        ident.append(f"Repository path: {rule.github_path}")
    ident.append(f"Community votes: +{rule.vote_up or 0} / -{rule.vote_down or 0}")
    parts.append("## Rule identity\n" + '\n'.join(ident))

    parts.append("## Description written by the author\n"
                 + (_clip(rule.description, DESC_CHARS) or "(no description provided)"))

    parts.append("## Tags on Rulezet\n" + (', '.join(tags) if tags else "(none)"))

    # ── ATT&CK ───────────────────────────────────────────────────────────
    if techniques:
        lines = []
        for t in techniques[:MAX_TECHNIQUES]:
            tactics = ', '.join(t.tactic_keys or []) or 'n/a'
            lines.append(f"- {t.technique_id} {t.name} (tactics: {tactics})"
                         + (f"\n  {_clip(t.description, TECHNIQUE_CHARS)}" if t.description else ''))
        if len(techniques) > MAX_TECHNIQUES:
            lines.append(f"- … and {len(techniques) - MAX_TECHNIQUES} more: "
                         + ', '.join(t.technique_id for t in techniques[MAX_TECHNIQUES:]))
        parts.append("## MITRE ATT&CK techniques linked to this rule\n" + '\n'.join(lines))
    else:
        parts.append("## MITRE ATT&CK techniques linked to this rule\n(none mapped on Rulezet)")

    # ── CVEs ─────────────────────────────────────────────────────────────
    if cve_ids:
        blocks = [_cve_block(c, cve_details.get(c)) for c in cve_ids[:MAX_CVES]]
        if len(cve_ids) > MAX_CVES:
            blocks.append(f"- … and {len(cve_ids) - MAX_CVES} more: {', '.join(cve_ids[MAX_CVES:])}")
        parts.append("## Vulnerabilities (CVE) linked to this rule — data from Vulnerability Lookup\n"
                     + '\n'.join(blocks))
    else:
        parts.append("## Vulnerabilities (CVE) linked to this rule\n(none)")

    # ── Quality signals ──────────────────────────────────────────────────
    breakdown = rule.quality_score_breakdown or {}
    if rule.quality_score is not None and isinstance(breakdown, dict):
        failing = []
        for cat, info in (breakdown.get('categories') or {}).items():
            for check, ok in ((info or {}).get('checks') or {}).items():
                if ok is False:
                    failing.append(f"{cat}: {check.replace('_', ' ')}")
        parts.append(f"## Rulezet quality score\n{round(rule.quality_score)}/100"
                     + ("\nFailing checks: " + '; '.join(failing) if failing else "\nAll quality checks pass."))

    # ── Relations / bundles ──────────────────────────────────────────────
    try:
        from app.features.rule_relation.rule_relation_core import get_relations_for_rule
        rel = get_relations_for_rule(rule_id)
        rel_lines = [f"- depends on / links to: {r['rule_title']} ({r['relation_type']})"
                     for r in rel['outgoing'][:MAX_RELATIONS]]
        rel_lines += [f"- used by / linked from: {r['rule_title']} ({r['relation_type']})"
                      for r in rel['incoming'][:MAX_RELATIONS]]
        if rel_lines:
            parts.append("## Linked rules\n" + '\n'.join(rel_lines))
    except Exception:
        db.session.rollback()

    bundles = (db.session.query(Bundle.name)
               .join(BundleRuleAssociation, BundleRuleAssociation.bundle_id == Bundle.id)
               .filter(BundleRuleAssociation.rule_id == rule_id, Bundle.access.is_(True))
               .distinct().limit(MAX_BUNDLES).all())
    if bundles:
        parts.append("## Public bundles shipping this rule\n" + ', '.join(name for (name,) in bundles))

    # ── Content ──────────────────────────────────────────────────────────
    parts.append("## Rule content\n```\n" + _clip(rule.to_string, CONTENT_CHARS) + "\n```")

    snapshot = {
        'cves': [
            {
                'id': c,
                'cvss': (cve_details.get(c) or {}).get('cvss_score') or None,
                'severity': ((cve_details.get(c) or {}).get('cvss_sev') or None)
                            if (cve_details.get(c) or {}).get('cvss_score') else None,
                'epss_pct': (cve_details.get(c) or {}).get('epss_pct'),
                'title': (cve_details.get(c) or {}).get('cna_title') or None,
            }
            for c in cve_ids[:MAX_CVES]
        ],
        'techniques': [{'id': t.technique_id, 'name': t.name} for t in techniques],
        'tag_count': len(tags),
        'quality_score': rule.quality_score,
    }
    return '\n\n'.join(parts), snapshot
