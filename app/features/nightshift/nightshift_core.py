"""nightshift_core.py — the hidden investigation game (see
docs/design/hidden_game_the_analyst.md): cases, pinned evidence, hints,
testing the player's rule against the case's samples, and the score.

The browser only ever sends what the player did (a pinned item, the blanks
of a rule); the rule is built, compiled and run here, and the score is
computed here — never taken from the client.
"""
import datetime
import glob
import hashlib
import json
import os
import re

from app import db
from app.core.db_class.nightshift import NightshiftAttempt, NightshiftCaseRun

CASES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cases')
MIN_SECONDS_BETWEEN_TESTS = 1
MAX_BLANK_LENGTH = 64
MATCH_TIMEOUT_S = 2

POINTS_CLOSED = 1000
POINTS_QUALITY = 700
POINTS_VARIANTS = 300
POINTS_EVIDENCE = 300
POINTS_BONUS_EVIDENCE = 200
POINTS_SPEED = 500
SPEED_COST_PER_TEST = 75
HINT_COST = 150
FAILED_DEPLOY_COST = 50

_ID_RE = re.compile(r'^[A-Za-z0-9-]{8,36}$')
_cases = {}


# ── Cases ────────────────────────────────────────────────────────────────

def _load_cases():
    if not _cases:
        for path in sorted(glob.glob(os.path.join(CASES_DIR, '*.json'))):
            with open(path, encoding='utf-8') as f:
                case = json.load(f)
            _cases[case['id']] = case
    return _cases


def get_case(case_id):
    return _load_cases().get(case_id)


def list_cases():
    return sorted(_load_cases().values(), key=lambda c: c['number'])


def _samples(case, *groups):
    return [s for g in groups for s in case['corpus'].get(g, [])]


def _sample_lines(sample):
    return sample['value'].split('\n')


def public_case(case):
    """What the browser may see: the story, the tools and the files' content —
    never which sample is malicious, the hidden variants or the reference rule."""
    by_id = {s['id']: s for s in _samples(case, 'malicious', 'benign')}
    files = []
    for f in case['tools']['files']:
        sample = by_id[f['sample']]
        data = sample['value'].encode('utf-8')
        files.append({
            'key': f['key'], 'name': f['name'], 'origin': f['origin'], 'sample': f['sample'],
            'size': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'lines': _sample_lines(sample),
        })
    visible = [{'id': s['id'], 'name': s['name'], 'expect': 'match'} for s in case['corpus']['malicious']] + \
              [{'id': s['id'], 'name': s['name'], 'expect': 'silent'} for s in case['corpus']['benign']]
    rule = case['rule']
    return {
        'id': case['id'], 'number': case['number'], 'time': case['time'], 'title': case['title'],
        'alert': case['alert'],
        'rulezy': {'intro': case['rulezy']['intro'], 'lines': case['rulezy']['lines'],
                   'hint_count': len(case['rulezy']['hints'])},
        'tools': {'mail': case['tools']['mail'], 'logs': case['tools']['logs'], 'files': files},
        'evidence': {'required': case['evidence']['required']},
        'rule': {'format': rule['format'], 'mode': rule['mode'], 'name': rule['name'],
                 'conditions': rule['conditions']},
        'samples': visible,
        'hidden_variant_count': len(case['corpus'].get('hidden_variants', [])),
    }


def _valid_evidence_keys(case):
    keys = {m['key'] for m in case['tools']['mail']}
    keys |= {f['key'] for f in case['tools']['files']}
    keys |= {log['key'] for log in case['tools']['logs']}
    return keys


def _is_valid_pin(case, key):
    if key in _valid_evidence_keys(case):
        return True
    # A line of a file: line:<sample id>:<line index>
    parts = key.split(':')
    if len(parts) == 3 and parts[0] == 'line' and parts[2].isdigit():
        shown = {f['sample'] for f in case['tools']['files']}
        if parts[1] in shown:
            sample = next(s for s in _samples(case, 'malicious', 'benign') if s['id'] == parts[1])
            return int(parts[2]) < len(_sample_lines(sample))
    return False


def _bonus_found(case, pinned):
    """Bonus evidence pinned. string:<sample>:<text> = any pinned line of that sample containing text."""
    by_id = {s['id']: s for s in _samples(case, 'malicious', 'benign')}
    found = []
    for bonus in case['evidence'].get('bonus', []):
        if bonus.startswith('string:'):
            _, sample_id, text = bonus.split(':', 2)
            lines = _sample_lines(by_id[sample_id])
            hit = any(p.startswith(f'line:{sample_id}:') and text in lines[int(p.rsplit(':', 1)[1])]
                      for p in pinned)
        else:
            hit = bonus in pinned
        if hit:
            found.append(bonus)
    return found


# ── Runs ─────────────────────────────────────────────────────────────────

def valid_player_id(value):
    return isinstance(value, str) and bool(_ID_RE.match(value))


def start_run(case_id, player_id, user_id):
    """The player's open run of this case (resumed), or a new one."""
    run = NightshiftCaseRun.query.filter_by(case_id=case_id, player_id=player_id, closed=False) \
        .order_by(NightshiftCaseRun.id.desc()).first()
    if run and run.user_id not in (None, user_id):
        run = None
    if run is None:
        run = NightshiftCaseRun(case_id=case_id, player_id=player_id, user_id=user_id, evidence=[])
        db.session.add(run)
    elif user_id and run.user_id is None:
        run.user_id = user_id
    db.session.commit()
    return run


def get_run(run_uuid, player_id, user_id):
    run = NightshiftCaseRun.query.filter_by(uuid=str(run_uuid)).first()
    if not run or run.player_id != player_id or run.user_id not in (None, user_id):
        return None
    return run


def run_state(run):
    case = get_case(run.case_id)
    hints = case['rulezy']['hints'][:run.hints_used]
    return {**run.to_json(), 'hints': hints}


def pin(run, key):
    case = get_case(run.case_id)
    if run.closed:
        return 'This case is closed.'
    if not isinstance(key, str) or len(key) > 120 or not _is_valid_pin(case, key):
        return 'Unknown evidence.'
    pinned = list(run.evidence or [])
    if key in pinned:
        pinned.remove(key)          # clicking a pinned item again unpins it
    else:
        pinned.append(key)
    run.evidence = pinned[:60]
    db.session.commit()
    return None


def take_hint(run):
    case = get_case(run.case_id)
    if run.closed:
        return 'This case is closed.'
    if run.hints_used >= len(case['rulezy']['hints']):
        return 'No more hints for this case.'
    run.hints_used += 1
    db.session.commit()
    return None


# ── Rule ─────────────────────────────────────────────────────────────────

def _yara_string(value):
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > MAX_BLANK_LENGTH or any(c in value for c in '\r\n\t\0'):
        return None
    if not value.isprintable():
        return None
    return value.replace('\\', '\\\\').replace('"', '\\"')


def build_rule(case, blanks):
    """The YARA rule from the case's template and the player's blanks, or (None, error)."""
    blanks = blanks if isinstance(blanks, dict) else {}
    a, b = _yara_string(blanks.get('a')), _yara_string(blanks.get('b'))
    condition = blanks.get('condition')
    if a is None or b is None:
        return None, f'Each string must be 1 to {MAX_BLANK_LENGTH} characters, on one line.'
    if condition not in case['rule']['conditions']:
        return None, 'Pick a condition.'
    # YARA refuses a string the condition never uses: declare only those it does.
    uses_all = 'them' in condition
    strings = ''.join(f'        ${n} = "{v}"\n' for n, v in (('a', a), ('b', b)) if uses_all or f'${n}' in condition)
    rule = f'rule {case["rule"]["name"]}\n{{\n    strings:\n{strings}    condition:\n        {condition}\n}}\n'
    return rule, None


def evaluate(rule, samples):
    """{sample id: matched} for each sample, or (None, error)."""
    try:
        import yara
    except ImportError:
        return None, 'The YARA engine is not installed on this server.'
    try:
        compiled = yara.compile(source=rule, includes=False)
    except Exception as e:
        return None, str(e)[:300]
    results = {}
    for s in samples:
        try:
            results[s['id']] = bool(compiled.match(data=s['value'].encode('utf-8'), timeout=MATCH_TIMEOUT_S))
        except Exception as e:
            return None, f'Scan error: {str(e)[:250]}'
    return results, None


def _visible_report(case, results):
    report, tp, fp, fn = [], 0, 0, 0
    for s in case['corpus']['malicious']:
        hit = results[s['id']]
        tp += hit
        fn += not hit
        report.append({'id': s['id'], 'name': s['name'], 'expect': 'match', 'matched': hit, 'ok': hit})
    for s in case['corpus']['benign']:
        hit = results[s['id']]
        fp += hit
        report.append({'id': s['id'], 'name': s['name'], 'expect': 'silent', 'matched': hit, 'ok': not hit})
    return report, tp, fp, fn


def _utcnow():
    """Naive UTC — what a DateTime column gives back, whatever the database's time zone."""
    return datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None)


def _too_fast(run):
    return bool(run.last_test_at) and (_utcnow() - run.last_test_at).total_seconds() < MIN_SECONDS_BETWEEN_TESTS


def check_rule(run, blanks, deploy=False):
    """Test (or deploy) the player's rule. Returns (result dict, error)."""
    case = get_case(run.case_id)
    if run.closed:
        return None, 'This case is closed.'
    if _too_fast(run):
        return None, 'Easy — one test per second.'
    if deploy and not set(case['evidence']['required']) <= set(run.evidence or []):
        return {'outcome': 'need_evidence'}, None

    rule, error = build_rule(case, blanks)
    if error:
        return None, error
    run.last_test_at = _utcnow()
    kind = 'deploy' if deploy else 'test'
    results, error = evaluate(rule, _samples(case, 'malicious', 'benign'))
    if error:
        db.session.add(NightshiftAttempt(run=run, kind=kind, rule=rule, error=error))
        if not deploy:
            run.tests += 1
        db.session.commit()
        return {'outcome': 'syntax', 'error': error, 'rule': rule}, None

    report, tp, fp, fn = _visible_report(case, results)
    db.session.add(NightshiftAttempt(run=run, kind=kind, rule=rule, tp=tp, fp=fp, fn=fn))
    result = {'rule': rule, 'samples': report, 'tp': tp, 'fp': fp, 'fn': fn}
    perfect = fp == 0 and fn == 0

    if not deploy:
        run.tests += 1
        db.session.commit()
        return {**result, 'outcome': 'ok' if perfect else ('fp' if fp else 'fn')}, None

    if not perfect:
        run.failed_deploys += 1
        db.session.commit()
        return {**result, 'outcome': 'deploy_fail'}, None

    variants = case['corpus'].get('hidden_variants', [])
    variant_results, _ = evaluate(rule, variants) if variants else ({}, None)
    variant_report = [{'id': v['id'], 'name': v['name'], 'matched': bool((variant_results or {}).get(v['id']))}
                      for v in variants]
    _close(run, case, rule, variant_report)
    db.session.commit()
    return {**result, 'outcome': 'closed', 'variants': variant_report, 'run': run_state(run)}, None


def score_case(case, run, variant_report):
    """The score of a closed case — every component, so the end screen can show them."""
    pinned = run.evidence or []
    bonus = case['evidence'].get('bonus', [])
    bonus_found = _bonus_found(case, pinned)
    side_found = [k for k in case['evidence'].get('side', []) if k in pinned]
    variants_caught = bool(variant_report) and all(v['matched'] for v in variant_report)

    details = {
        'closed': POINTS_CLOSED,
        'quality': POINTS_QUALITY + (POINTS_VARIANTS if variants_caught else 0),
        'investigation': POINTS_EVIDENCE + (POINTS_BONUS_EVIDENCE * len(bonus_found) // len(bonus) if bonus else 0),
        'speed': max(0, POINTS_SPEED - SPEED_COST_PER_TEST * max(0, run.tests - 1)),
        'hints': -HINT_COST * run.hints_used,
        'failed_deploys': -FAILED_DEPLOY_COST * run.failed_deploys,
    }
    total = max(0, sum(details.values()))
    stars = 1 + (run.failed_deploys == 0) + variants_caught
    return total, stars, {
        **details, 'bonus_found': len(bonus_found), 'bonus_total': len(bonus),
        'side_clues': len(side_found), 'variants_caught': variants_caught,
        'variants': variant_report,
    }


def _close(run, case, rule, variant_report):
    total, stars, details = score_case(case, run, variant_report)
    run.closed = True
    run.closed_at = datetime.datetime.now(tz=datetime.timezone.utc)
    run.rule = rule
    run.score, run.stars, run.score_details = total, stars, details
