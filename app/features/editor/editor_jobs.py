"""Background job behind the YARA editor's "Create": every rule is checked (already in Rulezet,
syntax with its dependencies, a test on sample sets — setting editor.test_on_create), and only
when everything passes are the rules created and linked; the test result is then kept with
each rule written. The steps and the per-rule report are kept in the job payload, so the
editor can show them while the job runs and put each error back on its line."""
from sqlalchemy.orm.attributes import flag_modified

from app import db
from app.core.db_class.rule import Rule
from app.core.db_class.user import User
from app.core.utils.app_settings import get_setting
from app.features.rule_tester import sample_test_core as SampleTests
from app.features.jobs.job_worker import register_handler

from . import editor_core as EditorModel
from . import external_checks as ExternalChecks

JOB_TYPE = 'editor_yara_import'

STEPS = [
    ('existing', 'Already in Rulezet?'),
    ('syntax', 'Syntax: each rule compiled with the rules it needs'),
    ('external', 'External checks: YARA-X, CCCS standard, yaraQA (advice)'),
    ('samples', 'Test on samples'),
    ('create', 'Create, update or propose, and link'),
]


def new_payload(imports, rules):
    return {
        'imports': imports,
        'rules': rules,
        'steps': [{'id': key, 'label': label, 'status': 'pending', 'detail': ''} for key, label in STEPS],
        'report': None,
        'ok': None,
        'result_url': None,
    }


def public_state(job):
    """What the editor polls: no rule texts, just progress and results."""
    payload = job.payload or {}
    return {
        'uuid': job.uuid,
        'status': job.status,
        'error': job.error,
        'steps': payload.get('steps', []),
        'ok': payload.get('ok'),
        'result_url': payload.get('result_url'),
        'created': (payload.get('report') or {}).get('created'),
        'updated': (payload.get('report') or {}).get('updated'),
        'proposed': (payload.get('report') or {}).get('proposed'),
        'rules': [{k: v for k, v in r.items() if k not in ('text', 'content')}
                  for r in ((payload.get('report') or {}).get('rules') or [])],
    }


@register_handler(JOB_TYPE)
def handle_editor_yara_import(job, app):
    payload = dict(job.payload or {})
    steps = {s['id']: s for s in payload['steps']}
    user = User.query.get(job.created_by)

    def save():
        payload['steps'] = [steps[key] for key, _ in STEPS]
        job.payload = dict(payload)
        flag_modified(job, 'payload')
        db.session.commit()

    def step(key, status, detail=''):
        steps[key].update(status=status, detail=detail)
        save()

    def progress(stage, done, total):
        steps[stage].update(status='running', detail=f'{done} / {total}')
        job.total = total
        job.done = done
        save()

    plan = EditorModel.plan_yara(payload.get('imports'), payload.get('rules') or [], progress, user)
    count = lambda *states: sum(1 for r in plan['rules'] if r['status'] in states)   # noqa: E731

    step('existing', 'ok', f"{count('exists')} already in Rulezet" if count('exists') else 'none')
    bad = count('error', 'blocked')
    step('syntax', 'error' if bad else 'ok', f'{bad} rule(s) to fix' if bad else f"{count('new', 'update', 'proposal')} rule(s) valid")
    run = None
    if plan['ok']:
        _external_checks(plan, payload, step)
        run = _test_on_samples(plan, payload, user, step)
    else:
        step('external', 'skipped', 'fix the errors first')
        step('samples', 'skipped', 'fix the errors first')
    if run and run.get('blocked'):
        plan['ok'] = False

    if not plan['ok']:
        payload.update(report=plan, ok=False)
        step('create', 'skipped', 'nothing created: fix the errors first')
        return

    step('create', 'running', f"{count('new', 'update', 'proposal')} rule(s)")
    result = EditorModel.create_from_plan(plan, user)
    payload.update(report=result, ok=result['ok'], result_url=result.get('result_url'))
    done = ', '.join(f'{n} {label}' for n, label in ((result.get('created'), 'created'), (result.get('updated'), 'updated'),
                                                    (result.get('proposed'), 'proposed')) if n) or 'nothing to write'
    step('create', 'ok' if result['ok'] else 'error', done + ('' if result['ok'] else ' — some rules were refused'))
    if run and run.get('status') == 'done':
        written = [(e['name'], Rule.query.get(e['created']['id'])) for e in result['rules']
                   if e['status'] in ('created', 'updated') and e.get('created')]
        SampleTests.record_rule_results(run, [(n, r) for n, r in written if r])


def _external_checks(plan, payload, step):
    """YARA-X, CCCS and yaraQA on the document (external_checks.py): advice shown with the result,
    never a reason to refuse — Rulezet's own syntax step above decides."""
    tools = ExternalChecks.enabled_tools()
    if not tools:
        step('external', 'skipped', 'switched off (setting editor.external_checks)')
        return
    step('external', 'running', ', '.join(tools))
    results = ExternalChecks.run_checks(EditorModel.test_document(plan, payload.get('imports')), tools)
    payload['external'] = results
    parts = []
    for tool, r in results.items():
        name = {'yarax': 'YARA-X', 'cccs': 'CCCS', 'yaraqa': 'yaraQA'}[tool]
        if not r.get('available'):
            parts.append(f'{name}: not available')
        else:
            n = len(r['errors']) + len(r['warnings'])
            parts.append(f"{name}: {n} remark{'s' if n != 1 else ''}" if n else f'{name}: ok')
    noisy = any(r.get('available') and (r['errors'] or r['warnings']) for r in results.values())
    step('external', 'warning' if noisy else 'ok', ' · '.join(parts))


def _test_on_samples(plan, payload, user, step):
    """Runs the document on the sample sets chosen by the setting (benign by default: false
    positives). A warning only, unless block_on_false_positives. Returns the run (or None)."""
    if not SampleTests.can_use_tests(user):
        step('samples', 'skipped', 'tests on samples are not enabled for you')
        return None
    conf = get_setting('editor.test_on_create') or {}
    if not any(e['status'] in ('new', 'update', 'proposal') for e in plan['rules']):
        step('samples', 'skipped', 'nothing new to test: every rule is already in Rulezet')
        return None
    if not conf.get('enabled', True):
        step('samples', 'skipped', 'switched off (setting editor.test_on_create)')
        return None
    service = EditorModel.create_test_service()
    if not service or 'yara' not in service.formats():
        step('samples', 'skipped', 'no test engine on this server')
        return None
    kinds = set(conf.get('kinds') or ['benign'])
    sets = [s['id'] for s in service.sets('yara') if s.get('kind') in kinds]
    if not sets:
        step('samples', 'skipped', 'no sample set to test on')
        return None
    step('samples', 'running', f'{len(sets)} sample set(s)')
    try:
        started = service.start('yara', EditorModel.test_document(plan, payload.get('imports')), sets,
                                 owner=user.id if user else None)
    except Exception as e:                       # TestError: a message for the user
        step('samples', 'warning', f'not run: {e}')
        return None
    run = service.registry.get(started['id']) or started
    if run.get('status') != 'done':
        step('samples', 'warning', f"not run: {run.get('error') or 'the test failed'}")
        return run
    summary = run.get('summary') or {}
    fp = summary.get('false_positives', 0)
    detail = f"{summary.get('total', 0)} samples · {fp} false positive{'s' if fp != 1 else ''}"
    if summary.get('detected') or summary.get('missed'):
        detail += f" · {summary.get('detected', 0)} detected, {summary.get('missed', 0)} missed"
    if fp and conf.get('block_on_false_positives'):
        step('samples', 'error', detail + ' — nothing created (setting editor.test_on_create)')
        return {**run, 'blocked': True}
    step('samples', 'warning' if fp else 'ok', detail)
    return run

