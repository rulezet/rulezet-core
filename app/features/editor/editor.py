"""Server side of the rule editor, mounted on /editor-api (validation, rule lookup, editor JS/CSS).
Logged-in users only, like the pages that show the editor."""
from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required
from rulezet_editor import create_blueprint

from . import editor_bundle as EditorBundle
from . import editor_core as EditorModel
from . import editor_jobs as EditorJobs

editor_blueprint = create_blueprint(EditorModel.backend, name='editor_api')


@editor_blueprint.before_request
def _login_required():
    if not current_user.is_authenticated:
        return jsonify({'error': 'Log in to use the editor.'}), 401
    return None


@editor_blueprint.post('/yara/plan')
def yara_plan():
    """Checks every rule of the document; creates nothing."""
    payload = request.get_json(silent=True) or {}
    return jsonify(EditorModel.plan_yara(payload.get('imports'), payload.get('rules') or [], user=current_user))


@editor_blueprint.post('/yara/import')
def yara_import():
    """Creates the new rules of the document, linked to the rules they need. Nothing is
    created when one rule has an error (409, the editor shows the errors)."""
    payload = request.get_json(silent=True) or {}
    result = EditorModel.import_yara(payload.get('imports'), payload.get('rules') or [], current_user)
    return jsonify(result), (200 if result.get('ok') else 409)



@editor_blueprint.post('/yara/jobs')
def yara_job_start():
    """Starts the checks + creation in the background; poll GET /yara/jobs/<uuid>."""
    from app.features.jobs.jobs_core import create_job
    payload = request.get_json(silent=True) or {}
    rules = [{'name': str(r.get('name') or ''), 'text': str(r.get('text') or ''),
              'path': str(r.get('path') or '') or None,
              'imports': [str(m) for m in (r.get('imports') or [])][:50] if r.get('imports') is not None else None}
             for r in (payload.get('rules') or [])][:EditorModel.MAX_RULES]
    if not rules:
        return jsonify({'error': 'No rule in the document.'}), 400
    imports = [str(m) for m in (payload.get('imports') or [])][:50]
    bundle = payload.get('bundle') or None
    if bundle:
        bundle = {'mode': 'update' if bundle.get('mode') == 'update' else 'create',
                  'bundle_id': int(bundle.get('bundle_id') or 0) or None,
                  'name': str(bundle.get('name') or '')[:255], 'description': str(bundle.get('description') or '')[:5000],
                  'public': bool(bundle.get('public', True))}
        error = EditorBundle.check_bundle_request(bundle, current_user)
        if error:
            return jsonify({'error': error}), 400
    label = f"YARA editor: {len(rules)} rule(s)" + (f" + bundle \"{bundle.get('name') or bundle.get('bundle_id')}\"" if bundle else '')
    job = create_job(EditorJobs.JOB_TYPE, EditorJobs.new_payload(imports, rules, bundle, payload.get('tree') if bundle else None),
                     label, current_user.id, total=len(rules))
    if not job:
        return jsonify({'error': 'Could not start the job.'}), 500
    return jsonify(EditorJobs.public_state(job)), 202


@editor_blueprint.get('/yara/jobs/<string:job_uuid>')
def yara_job_state(job_uuid):
    from app.core.db_class.job import BackgroundJob
    job = BackgroundJob.query.filter_by(uuid=job_uuid, job_type=EditorJobs.JOB_TYPE).first()
    if not job or (job.created_by != current_user.id and not current_user.is_admin()):
        return jsonify({'error': 'Job not found.'}), 404
    return jsonify(EditorJobs.public_state(job))



@editor_blueprint.get('/bundles/<int:bundle_id>')
def bundle_workspace(bundle_id):
    """A bundle as an editor workspace (folders, rule files with their content)."""
    from app.core.db_class.bundle import Bundle
    from app.features.bundle.bundle_core import can_view_bundle
    bundle = Bundle.query.get(bundle_id)
    if not bundle or not can_view_bundle(bundle):
        return jsonify({'error': 'Bundle not found.'}), 404
    return jsonify(EditorBundle.workspace_from_bundle(bundle, current_user))



@editor_blueprint.get('/yara/scenarios')
def yara_scenarios():
    """Test cases that fill the workspace (admins, or a development instance)."""
    from flask import current_app
    if not (current_user.is_admin() or current_app.debug):
        return jsonify({'error': 'Not available.'}), 403
    return jsonify({'scenarios': EditorModel.scenarios(current_user)})


# Rulezet pages of the editor (the blueprint above is the editor's JSON API)
editor_page_blueprint = Blueprint('editor', __name__)


@editor_page_blueprint.get('/')
@login_required
def workspace():
    """The editor as a full page: folders and files of YARA rules, create rules or a bundle.
    ?bundle=<id> opens a bundle."""
    from flask import current_app
    return render_template('editor/workspace.html', bundle_id=request.args.get('bundle', type=int),
                           show_scenarios=current_user.is_admin() or current_app.debug)


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
