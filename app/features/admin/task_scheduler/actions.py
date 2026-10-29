"""
actions.py — the Workflows tasks that are not a job on rules: send an email, notify the admins,
write to the activity log, call a webhook. Their job handlers are in job_handlers.py (action_*);
this module holds what they share: the launch context and the {variables} of their messages.

Variables in a message (subject, text, webhook body):
    {workflow}       the workflow's title
    {task}           this task's title
    {date} {time}    now, UTC
    {status}         the launch so far: "3 done, 1 failed"
    {failed_tasks}   titles of the tasks that failed in this launch ("none")
    {done_tasks}     titles of the tasks done in this launch
    {link}           the workflow's page
    and the instance's figures (FIGURES below: {total_rules}, {bad_rules}, {new_rules_24h}…),
    counted only when the text names them.
A variable that is not in this list is left as written.
"""
import datetime
import ipaddress
import re
import socket
from urllib.parse import urlparse

_VAR = re.compile(r'\{([a-z_]+)\}')


def run_context(job):
    """The workflow / task / launch a job was fired for (None values when run outside a workflow)."""
    from app.core.db_class.job import BackgroundJob
    from app.core.db_class.task_scheduler import AdminTaskRun
    run = AdminTaskRun.query.filter_by(job_uuid=job.uuid).first()
    task = run.schedule if run else None
    workflow = task.workflow if task else None
    done, failed = [], []
    if run and run.workflow_run_id:
        for tr in AdminTaskRun.query.filter_by(workflow_run_id=run.workflow_run_id).all():
            if tr.id == run.id:
                continue
            j = BackgroundJob.query.filter_by(uuid=tr.job_uuid).first() if tr.job_uuid else None
            status = j.status if j else tr.status
            (done if status == 'done' else failed if status == 'failed' else []).append(tr.schedule.title)
    return {'run': run, 'task': task, 'workflow': workflow, 'done': done, 'failed': failed}


def _since(hours):
    return datetime.datetime.utcnow() - datetime.timedelta(hours=hours)


def _total_rules():
    from app.features.rule.rule_core import _active
    return _active().count()


def _new_rules_24h():
    from app.core.db_class.rule import Rule
    from app.features.rule.rule_core import _active
    return _active().filter(Rule.creation_date >= _since(24)).count()


def _bad_rules():
    from app.core.db_class.rule import InvalidRuleModel
    return InvalidRuleModel.query.count()


def _failed_jobs_24h():
    from app.core.db_class.job import BackgroundJob
    return BackgroundJob.query.filter(BackgroundJob.status == 'failed',
                                      BackgroundJob.created_at >= _since(24)).count()


def _new_users_24h():
    from app.core.db_class.user import User
    return User.query.filter(User.created_at >= _since(24)).count()


# name → (label, how it is counted). Also the metrics of the "Check a figure" task.
FIGURES = {
    'total_rules':     ('Rules on the instance', _total_rules),
    'new_rules_24h':   ('Rules created in the last 24 h', _new_rules_24h),
    'bad_rules':       ('Bad rules (failed imports) waiting', _bad_rules),
    'failed_jobs_24h': ('Background jobs failed in the last 24 h', _failed_jobs_24h),
    'new_users_24h':   ('Accounts created in the last 24 h', _new_users_24h),
}


def figure(name):
    return FIGURES[name][1]()


def variables(ctx, base_url=''):
    now = datetime.datetime.utcnow()
    wf = ctx.get('workflow')
    parts = []
    if ctx['done']:
        parts.append(f"{len(ctx['done'])} done")
    if ctx['failed']:
        parts.append(f"{len(ctx['failed'])} failed")
    return {
        'workflow': wf.title if wf else 'Workflow',
        'task': ctx['task'].title if ctx.get('task') else 'Task',
        'date': now.strftime('%Y-%m-%d'), 'time': now.strftime('%H:%M UTC'),
        'status': ', '.join(parts) or 'first task of the launch',
        'failed_tasks': ', '.join(ctx['failed']) or 'none',
        'done_tasks': ', '.join(ctx['done']) or 'none',
        **{name: (lambda n=name: figure(n)) for name in FIGURES},   # counted on use
        'link': f"{base_url.rstrip('/')}/admin/tasks/{wf.uuid}" if wf else f"{base_url.rstrip('/')}/admin/tasks/",
    }


def render(text, values):
    """{name} replaced by its value; unknown names left as they are (never evaluated)."""
    def value(m):
        if m.group(1) not in values:
            return m.group(0)
        v = values[m.group(1)]
        return str(v() if callable(v) else v)
    return _VAR.sub(value, text or '')


OPERATORS = {'gt': ('>', lambda a, b: a > b), 'ge': ('≥', lambda a, b: a >= b),
             'lt': ('<', lambda a, b: a < b), 'le': ('≤', lambda a, b: a <= b),
             'eq': ('=', lambda a, b: a == b), 'ne': ('≠', lambda a, b: a != b)}


def public_https_url(url):
    """A webhook URL the server may call: https, no credentials, a host whose every address is
    public (resolved now — a name pointing at 127.0.0.1 / 10.x / 169.254.x is refused). Returns
    an error message or None."""
    try:
        p = urlparse(url or '')
    except Exception:
        return 'Not a URL.'
    if p.scheme != 'https' or not p.hostname:
        return 'The webhook must be an https:// URL.'
    if '@' in p.netloc:
        return 'No credentials in the URL (put a token in the body instead).'
    host = p.hostname.rstrip('.').lower()
    if host == 'localhost' or host.endswith('.localhost') or host.endswith('.internal') or host.endswith('.local'):
        return 'Local addresses are not allowed.'
    try:
        infos = socket.getaddrinfo(host, p.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return f'{host} does not resolve.'
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            return f'{host} points to a private or reserved address.'
    return None
