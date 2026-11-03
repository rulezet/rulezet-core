"""Server side of the rule editor, mounted on /editor-api (validation, rule lookup, editor JS/CSS).
Logged-in users only, like the pages that show the editor."""
from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
from rulezet_editor import create_blueprint

from app.features.rule_tester import sample_test_core as SampleTests

from . import editor_core as EditorModel
from . import editor_jobs as EditorJobs
from . import external_checks as ExternalChecks
from . import external_checks_sigma as ExternalChecksSigma

def _test_owner():
    return current_user.id if current_user.is_authenticated else None


# /editor-api/test/*: runs are private to the user who started them (the before_request below
# already refuses anonymous users)
editor_blueprint = create_blueprint(EditorModel.backend, name='editor_api',
                                    tests=EditorModel.tests, test_owner=_test_owner)


@editor_blueprint.before_request
def _login_required():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Log in to use the editor.'}), 401
    # the editor itself: only for who the admin allows (setting editor.access); the Samples tab of
    # rule pages also calls /editor-api/test, so tests are checked on their own setting below
    if not request.path.startswith('/editor-api/test'):
        # each format's editor has its own access setting (editor.access, editor.sigma_access)
        fmt = _request_format()
        allowed = SampleTests.can_use_editor(current_user, fmt) if fmt else \
            any(SampleTests.can_use_editor(current_user, f) for f in SampleTests.EDITOR_ACCESS_SETTINGS)
        if not allowed:
            return jsonify({'error': f"The {'Sigma' if fmt == 'sigma' else 'YARA' if fmt else 'rule'} editor is not available."}), 403
    # tests on samples: only for who the admin allows (setting editor.test_access)
    if request.path.startswith('/editor-api/test') and not SampleTests.can_use_tests(current_user):
        if request.method == 'GET' and request.path.rstrip('/').endswith('/sets'):
            return jsonify({'available': False, 'sets': []})
        return jsonify({'error': 'Tests on samples are not available.'}), 403
    return None


def _request_format():
    """The rule format a request of the editor is about: the /<format>/… path, else ?format= or the
    JSON body's format; None when it says none (assets, shared helpers)."""
    parts = request.path.split('/')
    if len(parts) > 2 and parts[2] in SampleTests.EDITOR_ACCESS_SETTINGS:
        return parts[2]
    fmt = request.args.get('format') or ((request.get_json(silent=True) or {}).get('format') if request.is_json else None)
    fmt = str(fmt or '').lower()
    return fmt if fmt in SampleTests.EDITOR_ACCESS_SETTINGS else None


@editor_blueprint.post('/external-checks')
def external_checks():
    """The format's external tools on the document, for the editor's Checks panel — advice next to
    Rulezet's own validation, never a verdict on saving. YARA: YARA-X / CCCS / yaraQA
    (external_checks.py); Sigma: SIEM conversion, SigmaHQ conventions, sigmalint, rsigma
    (external_checks_sigma.py). Other formats: none."""
    payload = request.get_json(silent=True) or {}
    text = payload.get('text')
    if not isinstance(text, str) or not text.strip():
        return jsonify({'error': 'No rule text.'}), 400
    fmt = str(payload.get('format') or 'yara').lower()
    module = {'yara': ExternalChecks, 'sigma': ExternalChecksSigma}.get(fmt)
    if not module:
        return jsonify({'results': {}})
    tools = payload.get('tools')
    tools = [t for t in tools if isinstance(t, str)] if isinstance(tools, list) else None
    return jsonify({'results': module.run_checks(text, tools)})


# Create of the editor, per format (yara, sigma): /<fmt>/plan, /<fmt>/import, /<fmt>/jobs
FMT = '<any(yara, sigma):fmt>'


@editor_blueprint.post(f'/{FMT}/plan')
def rules_plan(fmt):
    """Checks every rule of the document; creates nothing."""
    payload = request.get_json(silent=True) or {}
    return jsonify(EditorModel.plan(fmt, payload.get('imports'), payload.get('rules') or [], user=current_user))


@editor_blueprint.post(f'/{FMT}/import')
def rules_import(fmt):
    """Creates the new rules of the document (YARA: linked to the rules they need). Nothing is
    created when one rule has an error (409, the editor shows the errors)."""
    payload = request.get_json(silent=True) or {}
    result = EditorModel.import_rules(fmt, payload.get('imports'), payload.get('rules') or [], current_user)
    return jsonify(result), (200 if result.get('ok') else 409)



@editor_blueprint.post(f'/{FMT}/jobs')
def rules_job_start(fmt):
    """Starts the checks + creation in the background; poll GET /<fmt>/jobs/<uuid>."""
    from app.features.jobs.jobs_core import create_job
    payload = request.get_json(silent=True) or {}
    rules = [{'name': str(r.get('name') or ''), 'text': str(r.get('text') or ''),
              'path': str(r.get('path') or '') or None,
              'imports': [str(m) for m in (r.get('imports') or [])][:50] if r.get('imports') is not None else None,
              'fields': EditorModel.clean_fields(r.get('fields')),
              'id': r.get('id') if isinstance(r.get('id'), int) else None}
             for r in (payload.get('rules') or [])][:EditorModel.MAX_RULES]
    if not rules:
        return jsonify({'error': 'No rule in the document.'}), 400
    imports = [str(m) for m in (payload.get('imports') or [])][:50]
    # one Create at a time per user: each one compiles up to MAX_RULES rules and tests them
    from app.core.db_class.job import BackgroundJob
    if BackgroundJob.query.filter(BackgroundJob.job_type == EditorJobs.JOB_TYPE, BackgroundJob.created_by == current_user.id,
                                  BackgroundJob.status.in_(('pending', 'running'))).first():
        return jsonify({'error': 'A Create of yours is still running: wait for it to finish.'}), 429
    job = create_job(EditorJobs.JOB_TYPE, EditorJobs.new_payload(imports, rules, fmt),
                     f"{EditorModel._LABEL[fmt]} editor: {len(rules)} rule(s)", current_user.id, total=len(rules))
    if not job:
        return jsonify({'error': 'Could not start the job.'}), 500
    return jsonify(EditorJobs.public_state(job)), 202


@editor_blueprint.get('/yara/rules/<int:rule_id>/dependencies')
def yara_rule_dependencies(rule_id):
    """The rule and the rules it needs (edit page, YARA editor tab)."""
    data = EditorModel.rule_dependencies(rule_id, current_user)
    return jsonify(data) if data else (jsonify({'error': 'Rule not found.'}), 404)


@editor_blueprint.get(f'/{FMT}/jobs/<string:job_uuid>')
def rules_job_state(fmt, job_uuid):
    from app.core.db_class.job import BackgroundJob
    job = BackgroundJob.query.filter_by(uuid=job_uuid, job_type=EditorJobs.JOB_TYPE).first()
    if not job or (job.created_by != current_user.id and not current_user.is_admin()):
        return jsonify({'error': 'Job not found.'}), 404
    return jsonify(EditorJobs.public_state(job))



# Rulezet pages of the editor (the blueprint above is the editor's JSON API)
editor_page_blueprint = Blueprint('editor', __name__)


@editor_page_blueprint.get('/import-result')
@login_required
def import_result():
    """After "Create" in the YARA editor: every rule created or reused, with its links."""
    def ids(key):
        return [int(v) for v in request.args.getlist(key) if v.isdigit()]
    proposed = []
    for v in request.args.getlist('proposed'):
        rule_id, _, proposal_id = v.partition('-')
        if rule_id.isdigit() and proposal_id.isdigit():
            proposed.append((int(rule_id), int(proposal_id)))
    result = EditorModel.import_result(ids('created'), ids('reused'), ids('updated'), proposed)
    return render_template('editor/import_result.html', **result)
