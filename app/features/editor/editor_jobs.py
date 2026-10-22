"""Background job behind the YARA editor's "Create": every rule is checked (already in Rulezet,
syntax with its dependencies, samples later), and only when everything passes are the rules
created and linked. The steps and the per-rule report are kept in the job payload, so the
editor can show them while the job runs and put each error back on its line."""
from sqlalchemy.orm.attributes import flag_modified

from app import db
from app.core.db_class.user import User
from app.features.jobs.job_worker import register_handler

from . import editor_bundle as EditorBundle
from . import editor_core as EditorModel

JOB_TYPE = 'editor_yara_import'

STEPS = [
    ('existing', 'Already in Rulezet?'),
    ('syntax', 'Syntax: each rule compiled with the rules it needs'),
    ('samples', 'Test on samples'),
    ('create', 'Create, update or propose, and link'),
]


BUNDLE_STEP = ('bundle', 'Bundle: create it or update its files and folders')


def _steps(bundle):
    return STEPS + ([BUNDLE_STEP] if bundle else [])


def new_payload(imports, rules, bundle=None, tree=None):
    """bundle: {mode, bundle_id | name, description, public}; tree: the workspace (editor_bundle)."""
    return {
        'imports': imports,
        'rules': rules,
        'bundle': bundle,
        'tree': tree,
        'bundle_result': None,
        'steps': [{'id': key, 'label': label, 'status': 'pending', 'detail': ''} for key, label in _steps(bundle)],
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
        'bundle': payload.get('bundle_result'),
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
        payload['steps'] = [steps[key] for key, _ in _steps(payload.get('bundle'))]
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
    # tests on real samples come here (rule_tester); nothing blocks on them yet
    step('samples', 'skipped', 'coming soon')

    if not plan['ok']:
        payload.update(report=plan, ok=False)
        step('create', 'skipped', 'nothing created: fix the errors first')
        if payload.get('bundle'):
            step('bundle', 'skipped', 'no bundle: fix the errors first')
        return

    step('create', 'running', f"{count('new', 'update', 'proposal')} rule(s)")
    result = EditorModel.create_from_plan(plan, user)
    payload.update(report=result, ok=result['ok'], result_url=result.get('result_url'))
    done = ', '.join(f'{n} {label}' for n, label in ((result.get('created'), 'created'), (result.get('updated'), 'updated'),
                                                    (result.get('proposed'), 'proposed')) if n) or 'nothing to write'
    step('create', 'ok' if result['ok'] else 'error', done + ('' if result['ok'] else ' — some rules were refused'))

    spec = payload.get('bundle')
    if not spec or not result['ok']:
        if spec:
            step('bundle', 'skipped', 'no bundle: some rules were refused')
        return
    step('bundle', 'running', 'updating' if spec.get('mode') == 'update' else 'creating')
    rule_ids = {}
    for r in result['rules']:
        target = r.get('created') or r.get('existing')
        if target and target.get('id'):
            rule_ids[r['name']] = target['id']
    bundle, error = EditorBundle.write_bundle(spec, payload.get('tree') or [], rule_ids, user)
    if error:
        payload.update(ok=False)
        step('bundle', 'error', error)
        return
    payload['bundle_result'] = {'id': bundle.id, 'name': bundle.name, 'url': f'/bundle/detail/{bundle.id}',
                                'mode': spec.get('mode') or 'create'}
    step('bundle', 'ok', ('updated: ' if spec.get('mode') == 'update' else 'created: ') + bundle.name)
