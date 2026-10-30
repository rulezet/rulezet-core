"""
issue_report.py — "Create issue": a Markdown report, easy to read, to post as an issue on the rule's
repository (or anywhere). Two kinds:

  rule_report(rule)  what Rulezet's evaluation says about one rule — validation, external checks,
                     quality score (what is good, what is missing), votes, reviews, scopes,
                     the last failed update from its source;
  repo_report(repo)  what went wrong importing a Git source — its bad rules grouped by error (with
                     the file and the exact message), the rules referencing rules it can't find,
                     the invalid / weakest imported rules, failed updates.

Each comes with an "open an issue" link pre-filled for GitHub / GitLab repositories (the body is cut
to what a URL can carry; the full report is copied / downloaded from the window).
"""
import re
from collections import defaultdict
from urllib.parse import quote, urlparse

MAX_URL_BODY = 6000            # characters of the report put in the "new issue" URL
INSTANCE_LABEL = 'Rulezet'

_CHECK_LABELS = {
    'has_original_uuid': 'keeps its original id (UUID / sid)',
    'has_github_path': 'linked to its file in the repository',
    'has_source': 'says where it comes from',
    'has_description': 'has a description (30+ characters)',
    'has_author': 'has an author',
    'has_license': 'has a license',
    'says_how_written': 'says how it was written (human / AI)',
    'has_meaningful_tags': 'tagged (beyond tlp / pap)',
    'has_attack_mapping': 'mapped to MITRE ATT&CK',
    'passes_validation': "passes Rulezet's syntax check",
    'no_pending_failed_update': 'last update from its source succeeded',
    'reviewed_since_creation': 'looked at since creation',
    'approved_by_reviewer': 'approved in a review',
    'approved_by_two_reviewers': 'approved by two people',
    'no_changes_requested': 'no change requested on this version',
    'not_a_duplicate': 'not a copy of an older rule',
    'used_in_a_bundle': 'used in a bundle',
    'linked_to_a_threat': 'linked to a threat (CVE or ATT&CK)',
    'has_ai_analysis': 'has an AI analysis',
    'works_somewhere': 'reported working somewhere',
    'works_in_several_places': 'reported working in two places or more',
    'no_report_it_fails': 'no report that it fails',
    'tested_on_samples': 'tested on samples',
    'detects_its_samples': 'detects its samples',
    'no_false_positives': 'no false positive',
    'no_test_errors': 'ran without errors',
    'compiles_with_yara_x': 'compiles with YARA-X',
    'follows_cccs_standard': 'follows the CCCS YARA standard',
    'clean_for_yaraqa': 'no yaraQA issue',
}


def _label(key):
    if key in _CHECK_LABELS:
        return _CHECK_LABELS[key]
    return key.replace('format:', '').replace('_', ' ')


def _md(text, limit=600):
    """Text safe inside Markdown: no HTML, no breaking table / fence, trimmed."""
    text = str(text or '').replace('\r', '')
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    return (text[:limit] + '…') if len(text) > limit else text


def _code(text, limit=1500):
    text = str(text or '').replace('```', "'''")
    return (text[:limit] + '\n…') if len(text) > limit else text


def _repo_parts(url, provider=None):
    """(provider, base) for a GitHub / GitLab repository URL (self-hosted GitLab included, through
    Rulezet's own provider detection or the provider stored on the Git source), else (None, base)."""
    try:
        p = urlparse(url or '')
    except ValueError:
        return None, None
    host = (p.hostname or '').lower()
    path = p.path.rstrip('/').removesuffix('.git')
    if not host or path.count('/') < 2 or p.scheme not in ('http', 'https'):
        return None, None
    # A file / folder URL (…/blob/main/x.yar, …/-/tree/…, …/src/branch/…): keep the repository only
    path = path.split('/-/')[0]
    segs = path.strip('/').split('/')
    for i, seg in enumerate(segs[2:], start=2):
        if seg in ('blob', 'tree', 'raw', 'src', 'commit', 'issues', 'pulls', 'releases'):
            segs = segs[:i]
            break
    path = '/' + '/'.join(segs)
    base = f'{p.scheme}://{host}{path}'
    if provider not in ('github', 'gitlab', 'gitea'):      # unknown / "generic": ask Rulezet's detection (GIT_HOSTS)
        try:
            from app.features.rule.rule_format.utils_format.git_provider import detect_provider
            provider = detect_provider(base)
        except Exception:
            provider = None
    return (provider if provider in ('github', 'gitlab', 'gitea') else None), base


def blob_url(repo_url, path, branch=None, provider=None):
    provider, base = _repo_parts(repo_url, provider)
    if not base or not path:
        return None
    ref = branch or 'HEAD'
    if provider == 'gitlab':
        return f'{base}/-/blob/{ref}/{path.lstrip("/")}'
    if provider == 'gitea':
        return f'{base}/src/branch/{branch or "main"}/{path.lstrip("/")}'
    return f'{base}/blob/{ref}/{path.lstrip("/")}'


def new_issue_url(repo_url, title, body, provider=None):
    provider, base = _repo_parts(repo_url, provider)
    if not provider:
        return None
    if len(body) > MAX_URL_BODY:
        body = body[:MAX_URL_BODY] + '\n\n…_(report cut here — the full report is attached / pasted below)_'
    if provider in ('github', 'gitea'):          # Gitea / Forgejo take the same parameters
        return f'{base}/issues/new?title={quote(title)}&body={quote(body)}'
    return f'{base}/-/issues/new?issue%5Btitle%5D={quote(title)}&issue%5Bdescription%5D={quote(body)}'


# ── One rule ──────────────────────────────────────────────────────────────────

def _logo(base_url):
    """Rulezet logo at the top of the report (absolute URL: the issue lives on another site)."""
    base = (base_url or 'https://rulezet.org').rstrip('/')
    return f'<p align="center"><img src="{base}/static/image/rulezet_official_logo.png" alt="Rulezet" height="120"></p>\n'


def rule_report(rule, base_url=''):
    from app.core.db_class.rule import RuleReview, RuleScope, RuleUpdateHistory
    from app.features.editor.editor_core import validate
    from app.features.rule.rule_quality.quality_score_core import _content_hash, recompute_rule_quality_score

    rule_url = f"{base_url.rstrip('/')}/rule/detail_rule/{rule.id}"
    file_url = blob_url(rule.source, rule.github_path, getattr(rule, 'branch', None)) if rule.github_path else None
    lines = [_logo(base_url), f'## {INSTANCE_LABEL} report — `{_md(rule.title, 200)}`', '',
             f'**Format** {rule.format} · **Version** {_md(rule.version, 40) or "—"} · **UUID** `{rule.uuid}`'
             + (f' · **Original id** `{_md(rule.original_uuid, 80)}`' if rule.original_uuid and rule.original_uuid != rule.uuid else ''),
             f'**On {INSTANCE_LABEL}** {rule_url}']
    if file_url:
        lines.append(f'**File** [{_md(rule.github_path, 200)}]({file_url})')
    elif rule.source:
        lines.append(f'**Source** {_md(rule.source, 300)}')
    lines.append('')

    # Validation
    problems, good = [], []
    try:
        v = validate(rule.format, rule.to_string or '')
    except Exception:
        v = None
    if v is not None:
        if not v.ok:
            problems.append(('Syntax validation fails', [str(e) for e in (v.errors or [])][:10]))
        if getattr(v, 'warnings', None):
            problems.append(('Syntax warnings', [str(w) for w in v.warnings][:10]))

    # YARA external checks
    if (rule.format or '').lower() == 'yara':
        try:
            from app.features.editor.external_checks import run_checks
            for tool, res in run_checks(rule.to_string or '').items():
                if not res.get('available'):
                    continue
                name = {'yarax': 'YARA-X', 'cccs': 'CCCS YARA standard', 'yaraqa': 'yaraQA'}.get(tool, tool)
                msgs = [m.get('message', '') for m in (res.get('errors') or []) + (res.get('warnings') or [])]
                if msgs:
                    problems.append((name, msgs[:10]))
        except Exception:
            pass

    # Last failed update from its source
    last = (RuleUpdateHistory.query.filter_by(rule_id=rule.id)
            .order_by(RuleUpdateHistory.analyzed_at.desc()).first())
    if last is not None and last.success is False:
        problems.append(('Last update from its source failed', [_md(last.message, 400)]))

    # Quality score
    try:
        if rule.quality_score is None:
            recompute_rule_quality_score(rule)
    except Exception:
        pass
    breakdown = rule.quality_score_breakdown or {}
    missing = []
    for cat_key, cat in (breakdown.get('categories') or {}).items():
        if cat.get('not_applicable'):
            continue
        for check, ok in (cat.get('checks') or {}).items():
            (good if ok else missing).append(_label(check))

    lines.append('### Summary')
    lines.append(f"- **Quality score** {round(rule.quality_score) if rule.quality_score is not None else '—'} / 100"
                 + (f" (+{breakdown.get('engagement_boost')} community boost)" if breakdown.get('engagement_boost') else ''))
    lines.append(f'- **Votes** {rule.vote_up or 0} up · {rule.vote_down or 0} down')
    current = _content_hash(rule.to_string)
    reviews = RuleReview.query.filter_by(rule_id=rule.id).all()
    approvals = [r for r in reviews if r.verdict == 'approved' and r.content_hash == current]
    changes = [r for r in reviews if r.verdict == 'changes_requested' and r.content_hash == current]
    ratings = [r.rating for r in reviews if r.rating and r.content_hash == current]
    lines.append(f'- **Reviews** {len(approvals)} approval(s), {len(changes)} change request(s)'
                 + (f', average rating {round(sum(ratings) / len(ratings), 1)}/5' if ratings else ''))
    scopes = RuleScope.query.filter_by(rule_id=rule.id).all()
    if scopes:
        lines.append(f'- **Field reports** {sum(1 for s in scopes if s.works)} "works", {sum(1 for s in scopes if not s.works)} "doesn\'t work"')
    lines.append('')

    if problems:
        lines.append('### Problems found')
        for title, msgs in problems:
            lines.append(f'**{title}**')
            lines.append('```')
            lines += [_code(m, 400) for m in msgs]
            lines.append('```')
        lines.append('')
    if changes:
        lines.append('### Changes requested in reviews')
        for r in changes:
            who = r.user.get_username() if r.user else 'someone'
            lines.append(f'- **{_md(who, 60)}**: {_md(r.comment, 600) or "(no comment)"}')
        lines.append('')
    broken = [s for s in scopes if not s.works]
    if broken:
        lines.append("### Reported not working")
        for s in broken[:10]:
            env = ', '.join(f"{e.get('key')}={e.get('value')}" for e in (s.entries or [])) or 'no environment given'
            lines.append(f'- {_md(env, 200)}' + (f' — {_md(s.comment, 300)}' if s.comment else ''))
        lines.append('')
    if missing:
        lines.append('### What would improve it')
        lines += [f'- [ ] {m}' for m in missing]
        lines.append('')
    if good:
        lines.append('### What is good')
        lines += [f'- {g}' for g in dict.fromkeys(good)]
        lines.append('')
    lines.append(f'_Generated by {INSTANCE_LABEL} — {rule_url}_')

    md = '\n'.join(lines)
    title = f'[{INSTANCE_LABEL}] {rule.title[:100]}: ' + (f'{len(problems)} problem(s) found' if problems else 'evaluation report')
    provider, repo = _repo_parts(rule.source)
    repo = repo if provider else None
    return {'title': title, 'markdown': md, 'repo_url': repo, 'provider': provider,
            'issue_url': new_issue_url(repo, title, md) if repo else None,
            'file_name': re.sub(r'[^A-Za-z0-9_.-]+', '_', rule.title)[:80] + '_report.md'}


# ── A Git source ──────────────────────────────────────────────────────────────

_DEP_ERR = re.compile(r'(?i)undefined identifier|unknown rule|undeclared identifier|not defined|cannot find|unresolved|references? .*missing')


def _error_key(message):
    """The first error, one line, values blanked — so the same mistake groups together:
    no line / column numbers, quoted values become "…", value lists become […]."""
    text = (message or '').strip()
    m = re.match(r'^\[\s*([\'"])(.*?)\1\s*[,\]]', text, re.S)      # a Python list of messages: its first one
    first = m.group(2) if m else (text.splitlines()[0] if text else 'unknown error')
    first = re.sub(r'\[[^\[\]]{0,400}\]', '[…]', first)
    first = re.sub(r'line \d+|:\d+(:\d+)?|\(\d+\)', '', first)
    first = re.sub(r'"[^"]{1,80}"|\'[^\']{1,80}\'|`[^`]{1,80}`', '"…"', first)
    return re.sub(r'\s+', ' ', first).strip(' :;,-—')[:160] or "unknown error"


def repo_report(repo, base_url=''):
    from app.core.db_class.rule import InvalidRuleModel, Rule, RuleUpdateHistory
    from app.features.rule.rule_core import _active

    url = repo.url
    page = f"{base_url.rstrip('/')}/rule/github_detail?url={quote(url, safe='')}"
    counts = {b: n for b, n in (repo.branch_counts or {}).items() if b}
    default_branch = max(counts, key=counts.get) if counts else None     # the branch most of its rules come from
    bad = InvalidRuleModel.query.filter_by(url=url).order_by(InvalidRuleModel.file_name).all()
    rules = _active().filter(Rule.source == url).all()
    invalid = [r for r in rules if (((r.quality_score_breakdown or {}).get('categories') or {})
                                    .get('validity', {}).get('checks', {}).get('passes_validation') is False)]
    weak = sorted([r for r in rules if r.quality_score is not None and r.quality_score < 40], key=lambda r: r.quality_score)[:15]
    rule_ids = [r.id for r in rules]
    failed_updates = []
    if rule_ids:
        for h in (RuleUpdateHistory.query.filter(RuleUpdateHistory.rule_id.in_(rule_ids), RuleUpdateHistory.success == False)  # noqa: E712
                  .order_by(RuleUpdateHistory.analyzed_at.desc()).limit(200).all()):
            if h.rule_id not in {f.rule_id for f in failed_updates}:
                failed_updates.append(h)

    deps = [b for b in bad if _DEP_ERR.search(b.error_message or '')]
    groups = defaultdict(list)
    for b in bad:
        groups[_error_key(b.error_message)].append(b)

    qs = repo.quality_score
    lines = [_logo(base_url), f'## {INSTANCE_LABEL} import report — {url}', '',
             f'**Imported** {len(rules)} rule(s) · **Not imported (bad rules)** {len(bad)}'
             + (f' · **Source quality** {round(qs)}/100' if qs is not None else ''),
             f'**On {INSTANCE_LABEL}** {page}', '']
    if not bad and not invalid and not failed_updates:
        lines += ['### No problem found', 'Every file imported and every rule passes validation.', '']

    if bad:
        lines.append(f'### Files that could not be imported ({len(bad)})')
        lines.append('Grouped by error — fix one, the others of the group usually follow.')
        lines.append('')
        for key, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            lines.append(f'<details><summary><b>{_md(key, 160)}</b> — {len(items)} file(s)</summary>')
            lines.append('')
            for b in items[:40]:
                path = b.github_path or b.file_name
                link = blob_url(url, b.github_path, default_branch, repo.git_provider) if b.github_path else None
                lines.append(f'- {"[" + _md(path, 200) + "](" + link + ")" if link else "`" + _md(path, 200) + "`"} ({b.rule_type})')
                lines.append(f'  ```\n  {_code(b.error_message, 500).replace(chr(10), chr(10) + "  ")}\n  ```')
            if len(items) > 40:
                lines.append(f'- … and {len(items) - 40} more')
            lines.append('')
            lines.append('</details>')
            lines.append('')
    if deps:
        lines.append(f'### References that do not resolve ({len(deps)})')
        lines.append('These rules use another rule (or module) that is not in the repository or not importable:')
        lines += [f'- `{_md(b.github_path or b.file_name, 200)}` — {_md((b.error_message or "").splitlines()[0], 200)}' for b in deps[:40]]
        lines.append('')
    if invalid:
        lines.append(f'### Imported but failing validation now ({len(invalid)})')
        for r in invalid[:30]:
            link = blob_url(url, r.github_path, getattr(r, 'branch', None), repo.git_provider) if r.github_path else None
            lines.append(f'- {"[" + _md(r.title, 120) + "](" + link + ")" if link else _md(r.title, 120)}')
        lines.append('')
    if failed_updates:
        lines.append(f'### Updates from the repository that failed ({len(failed_updates)})')
        for h in failed_updates[:30]:
            lines.append(f'- **{_md(h.rule_title, 120)}** — {_md(h.message, 300)}')
        lines.append('')
    if weak:
        lines.append('### Weakest rules (quality score below 40)')
        for r in weak:
            miss = [_label(k) for c in ((r.quality_score_breakdown or {}).get('categories') or {}).values()
                    if not c.get('not_applicable') for k, ok in (c.get('checks') or {}).items() if not ok][:5]
            lines.append(f'- **{_md(r.title, 120)}** ({round(r.quality_score)}/100) — missing: {", ".join(miss) or "—"}')
        lines.append('')
    if qs is not None and repo.quality_breakdown:
        pts = repo.quality_breakdown.get('points') or {}
        w = repo.quality_breakdown.get('weights') or {}
        lines.append('### Source quality')
        lines += [f'- {k.replace("_", " ")}: {pts.get(k)}/{w.get(k)}' for k in w]
        lines.append('')
    lines.append(f'_Generated by {INSTANCE_LABEL} — {page}_')

    md = '\n'.join(lines)
    title = f'[{INSTANCE_LABEL}] Import report: {len(bad)} file(s) not imported' + (f', {len(invalid)} invalid' if invalid else '')
    provider = _repo_parts(url, repo.git_provider)[0]
    return {'title': title, 'markdown': md, 'repo_url': url, 'provider': provider,
            'issue_url': new_issue_url(url, title, md, provider),
            'file_name': re.sub(r'[^A-Za-z0-9_.-]+', '_', url.split('//')[-1])[:80] + '_import_report.md'}
