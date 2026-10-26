"""Tests on sample sets (app/modules/rulezet-tester) kept in Rulezet's database:

  - DbRunRegistry: where TestService keeps run states — one table row per run, so every web
    process (gunicorn) and the job worker see the same runs, and a run outlives a restart;
  - per-rule results: what a run said about each rule, for the version that was tested
    (sha256 of its text), read back for the "tested on N samples" badge of the rule page.
"""
import datetime
import hashlib
import re
from contextlib import nullcontext

from flask import current_app, has_app_context

from app import db
from app.core.db_class.rule_tester import RuleSampleResult, SampleTestRun


def content_hash(text):
    return hashlib.sha256((text or '').encode('utf-8', 'replace')).hexdigest()


def _when(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc) if ts else None


class DbRunRegistry:
    """TestService registry (get / save) on the sample_test_run table. Runs execute in worker
    threads with no Flask context: the app seen at the first call (always a request or the job
    worker) is kept to open one."""

    def __init__(self, origin='editor'):
        self.origin = origin
        self.app = None

    def _ctx(self):
        if has_app_context():
            self.app = self.app or current_app._get_current_object()
            return nullcontext()
        return self.app.app_context()

    def save(self, run):
        with self._ctx():
            row = SampleTestRun.query.filter_by(run_id=run['id']).first()
            if not row:
                row = SampleTestRun(run_id=run['id'], user_id=run.get('owner'), format=run.get('format') or '',
                                    origin=self.origin)
                db.session.add(row)
            row.status = run.get('status') or 'queued'
            row.state = dict(run)
            row.finished_at = _when(run.get('finished'))
            db.session.commit()

    def get(self, run_id):
        with self._ctx():
            row = SampleTestRun.query.filter_by(run_id=str(run_id)[:32]).first()
            return dict(row.state) if row else None


def rule_counts(run, rule_name):
    """One rule's share of a run: the run's samples seen through that rule's hits only (a
    document holds several rules; a sample "matched" by another rule is not this rule's)."""
    counts = {'total': 0, 'detected': 0, 'missed': 0, 'false_positives': 0, 'errors': 0}
    for smp in run.get('samples') or []:
        counts['total'] += 1
        if smp.get('verdict') in ('error', 'timeout'):
            counts['errors'] += 1
            continue
        hit = any(h.get('rule') == rule_name for h in smp.get('hits') or [])
        if smp.get('expected') == 'match':
            counts['detected' if hit else 'missed'] += 1
        elif smp.get('expected') == 'no_match' and hit:
            counts['false_positives'] += 1
    return counts


def record_rule_results(run, rules):
    """rules: [(rule_name_in_the_document, Rule)] written from the tested document."""
    row = SampleTestRun.query.filter_by(run_id=run['id']).first()
    if not row or run.get('status') != 'done':
        return 0
    sets = [{'id': s['id'], 'name': s['name'], 'kind': s['kind']} for s in run.get('sets') or []]
    for name, rule in rules:
        db.session.add(RuleSampleResult(rule_id=rule.id, run_id=row.id, content_hash=content_hash(rule.to_string),
                                        sets=sets, **rule_counts(run, name)))
    db.session.commit()
    return len(rules)


def latest_result(rule):
    """The newest result for the rule's current text, or None (never tested, or changed since)."""
    if not rule:
        return None
    found = (RuleSampleResult.query.filter_by(rule_id=rule.id, content_hash=content_hash(rule.to_string))
             .order_by(RuleSampleResult.created_at.desc(), RuleSampleResult.id.desc()).first())
    return found.to_json() if found else None


_RULE_NAME = re.compile(r'^\s*(?:(?:private|global)\s+)*rule\s+([A-Za-z_]\w*)', re.M)


def _sample_view(smp, rule_name):
    """One sample of a run seen through one rule: its own hits and outcome (never a path)."""
    hits = [h for h in smp.get('hits') or [] if h.get('rule') == rule_name]
    verdict = smp.get('verdict')
    if verdict in ('error', 'timeout', 'pending'):
        outcome = verdict
    elif smp.get('expected') == 'match':
        outcome = 'detected' if hits else 'missed'
    elif smp.get('expected') == 'no_match':
        outcome = 'false_positive' if hits else 'clean'
    else:
        outcome = 'matched' if hits else 'not_matched'
    return {
        'label': smp.get('label') or smp.get('id'), 'set': smp.get('set'), 'sha256': smp.get('sha256'),
        'size': smp.get('size'), 'expected': smp.get('expected'), 'outcome': outcome, 'time_ms': smp.get('time_ms'),
        'hits': [{k: h.get(k) for k in ('item', 'where', 'data', 'before', 'after')} for h in hits[:50]],
        'hit_count': len(hits),
    }


# one string definition: `$id = value`, up to the next definition (rules written on one line too)
_STRING_DEF = re.compile(r'(\$\w*)\s*=\s*(.+?)(?=\s+\$\w*\s*=|\s*$)', re.S)


def rule_strings(text, samples):
    """Each string declared in the rule's strings: section with what it did in the run: on how
    many samples it matched, how many of them it should (detected) or should not (false
    positives). A string that never matched is listed too: that is worth knowing."""
    section = re.search(r'\bstrings\s*:(.*?)\bcondition\s*:', text or '', re.S)
    found = []
    for m in _STRING_DEF.finditer(section.group(1) if section else ''):
        if m.group(1) in {f['id'] for f in found}:
            continue
        mine = [s for s in samples if any(h.get('item') == m.group(1) for h in s['hits'])]
        found.append({'id': m.group(1), 'definition': ' '.join(m.group(2).split())[:200], 'samples': len(mine),
                      'detected': sum(1 for s in mine if s['outcome'] == 'detected'),
                      'false_positives': sum(1 for s in mine if s['outcome'] == 'false_positive')})
    return found


def rule_sample_details(rule):
    """Everything the rule's "Samples" page shows: every result kept for the rule (newest first,
    each saying whether it is about the current text), and for the newest one of the current
    version its sets and samples seen through this rule."""
    current = content_hash(rule.to_string)
    rows = (RuleSampleResult.query.filter_by(rule_id=rule.id)
            .order_by(RuleSampleResult.created_at.desc(), RuleSampleResult.id.desc()).limit(50).all())
    history = [{**r.to_json(), 'id': r.id, 'current': r.content_hash == current,
                'origin': r.run.origin if r.run else None} for r in rows]
    latest = next((r for r in rows if r.content_hash == current), None)
    details = {'history': history, 'latest': None, 'sets': [], 'samples': [], 'strings': []}
    if not latest or not latest.run:
        return details
    state = latest.run.state or {}
    found = _RULE_NAME.search(rule.to_string or '')
    name = found.group(1) if found else rule.title
    samples = [_sample_view(s, name) for s in state.get('samples') or []]
    sets = []
    for st in state.get('sets') or []:
        mine = [s for s in samples if s['set'] == st['id']]
        sets.append({'id': st['id'], 'name': st['name'], 'kind': st['kind'], 'total': len(mine),
                     **{k: sum(1 for s in mine if s['outcome'] == k)
                        for k in ('detected', 'missed', 'false_positive', 'clean', 'matched', 'error', 'timeout')}})
    details['strings'] = rule_strings(rule.to_string, samples)
    set_names = {s['id']: s['name'] for s in sets}
    for s in samples:
        s['set_name'] = set_names.get(s['set'], s['set'])
    details.update(latest={**latest.to_json(), 'origin': latest.run.origin}, sets=sets, samples=samples)
    return details


def rule_sample_count(rule_id):
    return RuleSampleResult.query.filter_by(rule_id=rule_id).count()
