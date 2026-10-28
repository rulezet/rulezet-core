"""tour_core.py — the "Tutorial" button of every page and the full tour of Rulezet.

Texts are settings (app/config/, editable from Admin → Configuration):
  tour.enabled        the Tutorial button on or off
  tour.roles          the first step: who you are browsing as and what that lets you do
  tour.page.<endpoint> the hand-written tour of one page (endpoint as Flask names it, e.g.
                      tour.page.rule.rules_list); a page without one gets the generic tour,
                      built in the browser from the page's own title, description and sections
  tour.full           the full tour: an ordered list of pages, each with its steps
  tour.demo           the example rule and bundle shown when the instance has none

A step: {"target": CSS selector (optional: no target = a centred card), "title", "text",
         "roles": [...] (optional, who sees the step), "demo": "rule" | "bundle" (optional:
         shows the example in the card when the target is missing, e.g. an empty list)}.
Roles: "anonymous", "user" (any logged-in account, admins included), "member" (logged in,
not admin), "admin", "perm:<key>" (a role grant, e.g. perm:github.manage — admins have them all).
Steps are filtered here, on the server: a visitor never receives the admin steps.
"""
from flask import request, session, url_for
from flask_login import current_user

from app.core.utils.app_settings import get_setting

# Pages reachable under two endpoints share one tour (a code-level alias, not a setting)
ENDPOINT_ALIASES = {
    'rule.detail_rule_by_uuid': 'rule.detail_rule',
    'bundle.detail_uuid':       'bundle.detail',
}

# Endpoints that never show the button (login flow, error pages, embedded views)
NO_TOUR_ENDPOINTS = {'account.login', 'account.add_user', 'account.forgot_password',
                     'account.reset_password', 'account.acces_denied'}


def _setting(key, default=None):
    try:
        value = get_setting(key)
    except KeyError:
        return default
    return default if value is None else value


def user_roles(user=None) -> set:
    """The role names a step's "roles" list is matched against."""
    user = user or current_user
    if not getattr(user, 'is_authenticated', False):
        return {'anonymous'}
    roles = {'user'}
    if user.is_admin():
        roles.add('admin')
    else:
        roles.add('member')
        roles.update(f'perm:{key}' for key in _granted_permissions(user.id))   # one query, every page
    return roles


def _granted_permissions(user_id) -> list:
    """Permission keys granted to this user through their roles (admins have them all anyway)."""
    try:
        from app import db
        from app.core.db_class.role import Permission, RolePermission, UserRole
        rows = (db.session.query(Permission.key)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .join(UserRole, UserRole.role_id == RolePermission.role_id)
                .filter(UserRole.user_id == user_id).distinct().all())
        return [r[0] for r in rows]
    except Exception:
        return []


def _visible(step: dict, roles: set) -> bool:
    wanted = step.get('roles')
    return not wanted or bool(roles.intersection(wanted))


def filter_steps(steps, roles: set) -> list:
    return [s for s in (steps or []) if isinstance(s, dict) and _visible(s, roles)]


def page_key(endpoint: str | None) -> str | None:
    if not endpoint:
        return None
    return ENDPOINT_ALIASES.get(endpoint, endpoint)


def role_step(roles: set) -> dict | None:
    """First step of every tour: who you are browsing as (setting tour.roles)."""
    texts = _setting('tour.roles', {}) or {}
    if 'admin' in roles:
        main = texts.get('admin')
    elif 'user' in roles:
        main = texts.get('member')
    else:
        main = texts.get('anonymous')
    if not main:
        return None
    extra = [texts.get('permissions', {}).get(r[5:]) for r in sorted(roles)
             if r.startswith('perm:') and 'admin' not in roles]
    text = main.get('text', '') + ''.join(f'\n\n{e}' for e in extra if e)
    return {'title': main.get('title', 'Welcome'), 'text': text, 'role_badge': main.get('badge')}


def page_tour(endpoint: str | None, roles: set) -> dict | None:
    """The tour of this page for these roles, or None (the browser then builds the generic one)."""
    key = page_key(endpoint)
    doc = _setting(f'tour.page.{key}') if key else None
    if not isinstance(doc, dict):
        return None
    steps = filter_steps(doc.get('steps'), roles)
    return {'title': doc.get('title') or '', 'steps': steps} if steps else None


def _first_login_pending() -> bool:
    from app.core.db_class.user import User
    try:
        return User.query.filter_by(admin=True, must_change_password=True).first() is not None
    except Exception:
        return False


def instance_empty() -> bool:
    """No rule yet: a fresh Rulezet (the tour then starts by itself on the welcome page)."""
    try:
        from app.features.rule.rule_core import _active
        return _active().first() is None
    except Exception:
        return False


def create_starter(user) -> dict | None:
    """First visit of a logged-in user on an empty Rulezet: a real first rule and a bundle holding it
    (setting tour.demo), owned by that user, so the tour has something to show at every step.
    Nothing is created once the instance has a rule."""
    if not instance_empty():
        return None
    from app.features.bundle import bundle_core as BundleModel
    from app.features.rule import rule_core as RuleModel
    data = _setting('tour.demo', {}) or {}
    r, b = data.get('rule') or {}, data.get('bundle') or {}
    rule, message = RuleModel.add_rule_core({
        'title': r.get('title'), 'format': r.get('format', 'yara'), 'to_string': r.get('content', ''),
        'description': r.get('description', ''), 'license': 'MIT', 'source': 'Rulezet tutorial',
        'author': r.get('author', ''), 'version': r.get('version', '1.0'),
    }, user)
    if not rule or isinstance(rule, bool):
        return None
    bundle = BundleModel.create_bundle({'name': b.get('title'), 'description': b.get('description', ''),
                                        'public': True}, user)
    BundleModel.add_rule_to_bundle(bundle.id, rule.id, 'Added by the tutorial')
    return {'rule': url_for('rule.detail_rule', rule_id=rule.id), 'bundle': url_for('bundle.detail', bundle_id=bundle.id)}


def starter_links(user) -> dict | None:
    """Links to the first rule and bundle the tutorial created for this user (create_starter)."""
    if not getattr(user, 'is_authenticated', False):
        return None
    from app.core.db_class.bundle import Bundle
    from app.core.db_class.rule import Rule
    from app.features.rule.rule_core import _active
    rule = _active().filter(Rule.source == 'Rulezet tutorial', Rule.user_id == user.id).first()
    name = ((_setting('tour.demo', {}) or {}).get('bundle') or {}).get('title')
    bundle = Bundle.query.filter_by(user_id=user.id, name=name).first() if name else None
    if not rule or not bundle:
        return None
    return {'rule': url_for('rule.detail_rule', rule_id=rule.id), 'bundle': url_for('bundle.detail', bundle_id=bundle.id)}


def full_tour(roles: set, onboarding: bool = False) -> list:
    """The full tour for these roles: [{"page": endpoint, "url", "title", "steps": [...]}, ...].

    Each page starts with the whole page ("overview"), then goes section by section: the steps of
    that page's own tour (tour.page.<endpoint>) except the button-by-button ones ("level":
    "detail", kept for the page's own tour), then the page's extra "steps". A page with
    "when": "empty" is only part of it on an instance with no rule yet."""
    out = []
    empty = None
    for page in _setting('tour.full', []) or []:
        if not isinstance(page, dict) or not _visible(page, roles):
            continue
        if page.get('when') == 'empty' and not onboarding:     # onboarding: the starter rule exists now
            empty = instance_empty() if empty is None else empty
            if not empty:
                continue
        steps = []
        if page.get('overview'):
            steps.append({'target': '@page', 'title': page.get('title', ''), 'text': page['overview']})
        if page.get('sections', True) and page.get('page'):
            own = page_tour(page['page'], roles)
            steps += [s for s in (own or {}).get('steps', []) if s.get('level') != 'detail']
        steps += filter_steps(page.get('steps'), roles)
        url = _page_url(page)
        if steps and url:
            out.append({'page': page.get('page'), 'url': url, 'title': page.get('title', ''), 'steps': steps})
    return out


def _page_url(page: dict) -> str | None:
    """URL of a full-tour page. "sample": "rule" / "bundle" = a real public one when the instance
    has some, else the demo page (an example, never saved) — so the tour works on an empty Rulezet."""
    sample = page.get('sample')
    if sample:
        return sample_url(sample)
    if page.get('url'):
        return page['url']
    try:
        return url_for(page['page'])
    except Exception:
        return None


def sample_url(kind: str) -> str:
    if kind == 'rule':
        from app.features.rule.rule_core import _active
        from app.core.db_class.rule import Rule
        rule = _active().order_by(Rule.id.desc()).first()
        if rule:
            return url_for('rule.detail_rule', rule_id=rule.id)
    elif kind == 'bundle':
        from app.core.db_class.bundle import Bundle
        query = Bundle.query
        if hasattr(Bundle, 'access'):
            query = query.filter(Bundle.access.is_(True))
        bundle = query.order_by(Bundle.id.desc()).first()
        if bundle:
            return url_for('bundle.detail', bundle_id=bundle.id)
    return url_for('tour.demo', kind=kind if kind in ('rule', 'bundle') else 'rule')


def demo(kind: str) -> dict | None:
    data = _setting('tour.demo', {}) or {}
    return data.get(kind)


def context() -> dict | None:
    """What base.html embeds for the Tutorial button (None: no button on this page)."""
    if not _setting('tour.enabled', True):
        return None
    if getattr(current_user, 'must_change_password', False):      # first login: the profile page only
        return None
    endpoint = request.endpoint
    if not endpoint or endpoint in NO_TOUR_ENDPOINTS or endpoint == 'static':
        return None
    roles = user_roles()
    return {
        'page': page_key(endpoint),
        'roles': sorted(roles),
        'intro': role_step(roles),
        'tour': page_tour(endpoint, roles),
        'full_url': url_for('tour.full_tour_data'),
        'demo': _setting('tour.demo', {}),
        # a fresh, empty Rulezet: the full tour starts by itself on the home page (once per browser);
        # logged in, a first rule and bundle are created for it (create_starter)
        'autostart': endpoint == 'home.home' and instance_empty(),
        # nobody has set up the first admin yet: the home page only thanks and sends to the login
        'setup_pending': endpoint == 'home.home' and 'anonymous' in roles and _first_login_pending(),
        # the first admin just set up the account (account.edit_user): confetti, then the tour at once
        'just_setup': endpoint == 'home.home' and bool(session.pop('rz_just_setup', False)),
        'logged_in': 'user' in roles,
        'starter_url': url_for('tour.starter'),
    }
