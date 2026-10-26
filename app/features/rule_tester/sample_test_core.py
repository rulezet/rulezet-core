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
                                        rule_text=rule.to_string, sets=sets, **rule_counts(run, name)))
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


def _tested_text(rule, result):
    """The rule's text as it was when `result` was produced: kept on the result; for older results,
    found in the rule's history by its hash; the current text when it is that version."""
    if result.rule_text:
        return result.rule_text
    if content_hash(rule.to_string) == result.content_hash:
        return rule.to_string
    from app.core.db_class.rule import RuleUpdateHistory
    for h in RuleUpdateHistory.query.filter_by(rule_id=rule.id).order_by(RuleUpdateHistory.id.desc()).limit(200):
        for text in (h.new_content, h.old_content):
            if text and content_hash(text) == result.content_hash:
                return text
    return None


def rule_sample_details(rule, result_id=None):
    """Everything the rule's "Samples" page shows: every result kept for the rule (newest first,
    each saying whether it is about the current text), and one report in full — the one asked for
    (?result=), else the newest of the current version: its sets, its samples seen through this
    rule, and the rule as it was tested (its strings, its code)."""
    current = content_hash(rule.to_string)
    rows = (RuleSampleResult.query.filter_by(rule_id=rule.id)
            .order_by(RuleSampleResult.created_at.desc(), RuleSampleResult.id.desc()).limit(50).all())
    history = [{**r.to_json(), 'current': r.content_hash == current,
                'origin': r.run.origin if r.run else None} for r in rows]
    chosen = next((r for r in rows if r.id == result_id), None) if result_id else None
    shown = chosen or next((r for r in rows if r.content_hash == current), None)
    details = {'history': history, 'latest': None, 'sets': [], 'samples': [], 'strings': [],
               'rule_text': rule.to_string, 'selected_id': None, 'is_current': True}
    if not shown or not shown.run:
        return details
    text = _tested_text(rule, shown)
    state = shown.run.state or {}
    found = _RULE_NAME.search(text or rule.to_string or '')
    name = found.group(1) if found else rule.title
    samples = [_sample_view(s, name) for s in state.get('samples') or []]
    sets = []
    for st in state.get('sets') or []:
        mine = [s for s in samples if s['set'] == st['id']]
        sets.append({'id': st['id'], 'name': st['name'], 'kind': st['kind'], 'total': len(mine),
                     **{k: sum(1 for s in mine if s['outcome'] == k)
                        for k in ('detected', 'missed', 'false_positive', 'clean', 'matched', 'error', 'timeout')}})
    details['strings'] = rule_strings(text or '', samples)
    set_names = {s['id']: s['name'] for s in sets}
    for s in samples:
        s['set_name'] = set_names.get(s['set'], s['set'])
    details.update(latest={**shown.to_json(), 'origin': shown.run.origin}, sets=sets, samples=samples,
                   rule_text=text or '', selected_id=shown.id, is_current=shown.content_hash == current,
                   text_missing=text is None)
    return details


def rule_sample_count(rule_id):
    return RuleSampleResult.query.filter_by(rule_id=rule_id).count()


def _squash(text):
    """Text without any whitespace, lower case: a rule is found in a document whatever its layout."""
    return re.sub(r'\s+', '', text or '').lower()


def record_editor_run(run, text):
    """A run started from the editor's Test button: every YARA rule of Rulezet whose saved text is
    in the tested document unchanged — the rule of the edit page and the rules it needs — keeps
    the result for that version, when the user who ran it may edit the rule (owner or admin).
    A rule changed in the editor and not saved yet is not this version: nothing is recorded."""
    from sqlalchemy import func
    from app.core.db_class.rule import Rule
    from app.core.db_class.user import User
    from app.features.rule.rule_core import _active
    if not run or run.get('status') != 'done' or (run.get('format') or '').lower() != 'yara':
        return 0
    user = db.session.get(User, run.get('owner')) if run.get('owner') else None
    names = set(_RULE_NAME.findall(text or '')) | set(re.findall(r'\brule\s+([A-Za-z_]\w*)', text or ''))
    if not user or not names:
        return 0
    document = _squash(text)
    found = []
    for rule in _active().filter(Rule.corpus_identifier.in_(names), func.lower(Rule.format) == 'yara'):
        if (rule.user_id == user.id or user.is_admin()) and rule.to_string and _squash(rule.to_string) in document:
            found.append((rule.corpus_identifier, rule))
    return record_rule_results(run, found) if found else 0


def keep_document(run_id, text):
    """The text a Test-button run tested, kept on its row (never in the state sent to the browser)."""
    row = SampleTestRun.query.filter_by(run_id=str(run_id)[:32]).first()
    if row:
        row.document = text
        db.session.commit()


SAVED_AFTER_TEST_HOURS = 24


def record_saved_rule(rule, user):
    """A rule just saved (edit page): when the user tested exactly this text with the Test button
    in the last hours, that run's result is kept for this new version."""
    import datetime
    if not rule or not user or (rule.format or '').lower() != 'yara':
        return 0
    if rule.user_id != user.id and not user.is_admin():
        return 0
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=SAVED_AFTER_TEST_HOURS)
    wanted = _squash(rule.to_string)
    runs = (SampleTestRun.query.filter(SampleTestRun.user_id == user.id, SampleTestRun.origin == 'editor',
                                       SampleTestRun.status == 'done', SampleTestRun.document.isnot(None),
                                       SampleTestRun.created_at >= since)
            .order_by(SampleTestRun.created_at.desc()).limit(20).all())
    for row in runs:
        if wanted and wanted in _squash(row.document):
            if RuleSampleResult.query.filter_by(rule_id=rule.id, run_id=row.id).first():
                return 0
            return record_rule_results(row.state, [(rule.corpus_identifier or rule.title, rule)])
    return 0
