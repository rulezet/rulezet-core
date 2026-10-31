"""
ai_provenance.py — what an AI analysis is about, exactly (issues #88 / #89).

    content_hash(text)            the identity of a rule revision: sha256 of its content (line ends normalised)
    scope_for(script)             what the model really receives, and what it does NOT check
    provenance(generation, rule)  who asked / approved / started it, model, depth, revision, outdated, scope
    effective_execution(request)  queued / running / completed / failed — from the request, else its job

A request pins the rule's content when it is made (AIAnalysisRequest.input_content / content_hash); the
job analyses that content, never a newer version; the report keeps the hash it analysed. A report whose
hash differs from the rule's current content is "outdated" — whatever its age. Reports made before this
was recorded show "not recorded", never a guessed identity.
"""
from __future__ import annotations

import hashlib

# What the model is given, by script (rule_analysis_agent.py / rule_deep_analysis_agent.py)
_SCOPE = {
    'standard': ['Rule content (the pinned revision)', 'Title and description', 'Format', 'Tags',
                 'ATT&CK techniques linked to the rule', 'CVE identifiers linked to the rule'],
    'deep': ['Rule content (the pinned revision)', 'Title and description', 'Format', 'Tags',
             'ATT&CK techniques with their descriptions', 'CVE details from Vulnerability Lookup (CVSS, EPSS)',
             "Rulezet's quality checks of the rule", 'Rules linked to it'],
}
# What an AI analysis never is — shown with every report, so it is not read as a test result
NOT_CHECKED = ['Running the rule (syntax is validated by Rulezet, not by the AI)',
               'Behaviour on real files or traffic (sample tests, when there are, are linked separately)',
               'Confirmed security impact — it is an interpretation by a language model']


def content_hash(text: str | None) -> str:
    norm = '\n'.join(line.rstrip() for line in (text or '').replace('\r\n', '\n').strip().split('\n'))
    return hashlib.sha256(norm.encode('utf-8')).hexdigest()


def scope_for(script: str) -> dict:
    return {'inputs': list(_SCOPE.get(script, _SCOPE['standard'])), 'not_checked': list(NOT_CHECKED)}


def _who(user):
    if not user:
        return None
    return {'id': user.id, 'name': f'{user.first_name or ""} {user.last_name or ""}'.strip() or user.email}


def provenance(gen, rule=None) -> dict:
    """Labels for one report. `rule`: the rule now, to tell whether the report is outdated."""
    meta = gen.meta or {}
    script = meta.get('script') or 'standard'
    recorded = gen.content_hash is not None
    current = content_hash(rule.to_string) if rule is not None else None
    req = None
    if gen.request_id:
        from app import db
        from app.core.db_class.ai import AIAnalysisRequest
        req = db.session.get(AIAnalysisRequest, gen.request_id)
    return {
        'script': script,
        'model': gen.model,
        'created_at': (gen.created_at.isoformat() + ('' if gen.created_at.tzinfo else 'Z')) if gen.created_at else None,
        'recorded': recorded,
        # identities: only what was recorded — direct runs have no request / approver
        'requested_by': _who(gen.requested_by) if recorded else None,
        'approved_by': _who(gen.approved_by) if recorded else None,
        'initiated_by': _who(gen.initiated_by) if recorded else None,
        'run_as': _who(gen.user),
        'request_uuid': req.uuid if req else None,
        'job_uuid': gen.job_uuid,
        'content_hash': gen.content_hash,
        'outdated': bool(recorded and current and gen.content_hash != current),
        'scope': meta.get('scope') or (scope_for(script) if recorded else None),
    }


_JOB_TO_EXECUTION = {'pending': 'queued', 'running': 'running', 'paused': 'queued', 'done': 'completed',
                     'completed': 'completed', 'failed': 'failed', 'cancelled': 'failed'}


def effective_execution(req) -> str:
    """The request's execution status, corrected by its job: a job that ended without completing the
    request (crash, cancel, server restart) makes it "failed" — never stuck "queued" forever."""
    status = req.execution_status or 'not_started'
    if req.status != 'accepted':
        return 'not_started'
    if status in ('completed', 'failed'):
        return status
    if not req.job_uuid:
        return status
    from app.core.db_class.job import BackgroundJob
    job = BackgroundJob.query.filter_by(uuid=req.job_uuid).first()
    if not job:
        return 'failed'
    from_job = _JOB_TO_EXECUTION.get(job.status, status)
    if job.status in ('done', 'completed') and req.target_type == 'rule' and status in ('queued', 'running'):
        return 'failed' if req.generation_id is None and req.input_content else 'completed'
    return from_job if status in ('queued', 'running', 'not_started') else status
