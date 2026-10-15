"""
git_provider.py — one place that knows how to talk to a git hosting service.

Rules can be imported from any git repository: GitHub (github.com or a
GitHub Enterprise Server set as GITHUB_HOST), GitLab (gitlab.com or
self-hosted), Gitea / Forgejo / Codeberg, Bitbucket, or any plain git server.
Everything that needs "the branches of this repo", "its metadata", "its
default branch" or "clone it with credentials" goes through here, so
callers never hard-code one host's API.

Configuration (.env, editable in Admin → Settings):
    GITHUB_TOKEN     token for GITHUB_HOST (unchanged)
    GITHUB_HOST      github.com, or a GitHub Enterprise host
    GIT_HOSTS        extra git hosts, comma separated, optionally with their
                     type: "git.corp.lan=gitlab, code.example.org=gitea, git.example.net"
    GIT_HOST_TOKENS  per-host access tokens, comma separated:
                     "gitlab.com=glpat-xxx, git.corp.lan=yyy"

A host listed in GIT_HOST_TOKENS is a known git host too. The provider of a
host is, in order: the type given in GIT_HOSTS, a well-known public host,
a hint in the hostname ("gitlab.", "gitea.", "forgejo."), else "generic"
(plain git: clone, pull and `git ls-remote` only — no API).
"""
import base64
import os
import re
import subprocess
from urllib.parse import urlparse, quote

import requests


PROVIDERS = ('github', 'gitlab', 'gitea', 'bitbucket', 'generic')

PROVIDER_LABELS = {
    'github': 'GitHub',
    'gitlab': 'GitLab',
    'gitea': 'Gitea / Forgejo',
    'bitbucket': 'Bitbucket',
    'generic': 'Git',
}

PROVIDER_ICONS = {
    'github': 'fa-brands fa-github',
    'gitlab': 'fa-brands fa-gitlab',
    'gitea': 'fa-solid fa-mug-hot',
    'bitbucket': 'fa-brands fa-bitbucket',
    'generic': 'fa-brands fa-git-alt',
}

_PUBLIC_HOSTS = {
    'github.com': 'github',
    'gitlab.com': 'gitlab',
    'framagit.org': 'gitlab',
    'salsa.debian.org': 'gitlab',
    'gitlab.gnome.org': 'gitlab',
    'invent.kde.org': 'gitlab',
    'codeberg.org': 'gitea',
    'gitea.com': 'gitea',
    'bitbucket.org': 'bitbucket',
}

_HOST_HINTS = (('gitlab', 'gitlab'), ('forgejo', 'gitea'), ('gitea', 'gitea'))

# Basic-auth user name each service expects in front of a token.
_TOKEN_USER = {
    'github': 'x-access-token',
    'gitlab': 'oauth2',
    'gitea': 'token',
    'bitbucket': 'x-token-auth',
    'generic': 'oauth2',
}

_SPLIT_RE = re.compile(r'[,\s]+')


# ── Configuration ────────────────────────────────────────────────────────────

def _parse_host_map(raw: str) -> dict:
    out = {}
    for item in _SPLIT_RE.split(raw or ''):
        item = item.strip()
        if not item:
            continue
        host, _, value = item.partition('=')
        host = host.strip().lower().strip('/')
        if host:
            out[host] = value.strip()
    return out


def get_github_host() -> str:
    """Host treated as GitHub — github.com, or a GitHub Enterprise Server set
    as GITHUB_HOST (Admin → Settings)."""
    host = os.environ.get('GITHUB_HOST', 'github.com').strip().strip('/').lower()
    return host or 'github.com'


def configured_hosts() -> dict:
    """{host: provider or ''} from GIT_HOSTS + GIT_HOST_TOKENS."""
    hosts = {h: '' for h in _parse_host_map(os.environ.get('GIT_HOST_TOKENS'))}
    for host, kind in _parse_host_map(os.environ.get('GIT_HOSTS')).items():
        hosts[host] = kind.lower() if kind.lower() in PROVIDERS else ''
    return hosts


def known_hosts() -> set:
    """Every host whose URLs count as git repositories."""
    return {get_github_host(), *_PUBLIC_HOSTS, *configured_hosts()}


def get_host_token(host: str) -> str | None:
    host = (host or '').lower()
    if host == get_github_host() and os.environ.get('GITHUB_TOKEN'):
        return os.environ.get('GITHUB_TOKEN')
    return _parse_host_map(os.environ.get('GIT_HOST_TOKENS')).get(host) or None


# ── URL helpers ──────────────────────────────────────────────────────────────

def split_repo_url(url: str) -> tuple[str, str]:
    """(host, 'group/sub/repo') — path without leading/trailing '/' nor '.git'."""
    parsed = urlparse((url or '').strip())
    path = parsed.path.strip('/')
    if path.endswith('.git'):
        path = path[:-4]
    return (parsed.hostname or '').lower(), path


def normalize_repo_url(url: str) -> str:
    """https://host/path — what Rule.source stores for an imported repo."""
    url = (url or '').strip().rstrip('/')
    return url[:-4] if url.endswith('.git') else url


def detect_provider(url_or_host: str) -> str:
    host = url_or_host if '/' not in (url_or_host or '') else split_repo_url(url_or_host)[0]
    host = (host or '').lower()
    if not host:
        return 'generic'
    if host == get_github_host():
        return 'github'
    kind = configured_hosts().get(host)
    if kind:
        return kind
    if host in _PUBLIC_HOSTS:
        return _PUBLIC_HOSTS[host]
    for hint, kind in _HOST_HINTS:
        if hint in host:
            return kind
    return 'generic'


def is_known_git_host(host: str) -> bool:
    host = (host or '').lower()
    return host in known_hosts() or any(h in host for h, _ in _HOST_HINTS)


def is_git_repo_url(url: str) -> bool:
    """True for an http(s) URL on a known git host with an owner/repo path —
    i.e. a rule source that belongs in the imported repositories list."""
    try:
        parsed = urlparse(url or '')
    except ValueError:
        return False
    if parsed.scheme not in ('http', 'https'):
        return False
    host, path = split_repo_url(url)
    return is_known_git_host(host) and len([p for p in path.split('/') if p]) >= 2


def repo_owner(url: str) -> str | None:
    """First path segment — the user / organisation / top-level group."""
    _, path = split_repo_url(url)
    return path.split('/')[0] if path else None


def repo_display_name(url: str) -> str:
    """'owner/repo' (or 'group/sub/repo' on GitLab) for labels."""
    return split_repo_url(url)[1] or url


def provider_info(url: str) -> dict:
    kind = detect_provider(url)
    return {'provider': kind, 'label': PROVIDER_LABELS[kind], 'icon': PROVIDER_ICONS[kind]}


def tree_url(url: str, branch: str, path: str = '') -> str:
    """Web page of a folder on a branch — each host spells it differently."""
    base = normalize_repo_url(url)
    tail = f"{branch}/{path.strip('/')}".rstrip('/')
    kind = detect_provider(url)
    if kind == 'gitlab':
        return f'{base}/-/tree/{tail}'
    if kind == 'gitea':
        return f'{base}/src/branch/{tail}'
    if kind == 'bitbucket':
        return f'{base}/src/{tail}'
    return f'{base}/tree/{tail}'


# ── Credentials for git itself ───────────────────────────────────────────────

def authed_remote_url(url: str, token: str) -> str:
    """https://<user>:<token>@host/path.git — only for writing into a clone's
    own .git/config (never a process argument)."""
    host, path = split_repo_url(url)
    port = urlparse(url).port
    netloc = f'{host}:{port}' if port else host
    user = _TOKEN_USER[detect_provider(host)]
    return f'https://{user}:{quote(token, safe="")}@{netloc}/{path}.git'


def plain_remote_url(url: str) -> str:
    return normalize_repo_url(url) + '.git'


def git_env(url: str) -> dict:
    """Environment for a `git` process working on *url*: never prompt, and
    send the host's token (if one is configured) as an HTTP header. Passed
    through GIT_CONFIG_* (git >= 2.31) so the token is neither written to the
    clone's .git/config nor visible in the process list."""
    env = {'GIT_TERMINAL_PROMPT': '0'}
    host, _ = split_repo_url(url)
    token = get_host_token(host)
    if token:
        user = _TOKEN_USER[detect_provider(host)]
        basic = base64.b64encode(f'{user}:{token}'.encode()).decode()
        env.update({
            'GIT_CONFIG_COUNT': '1',
            'GIT_CONFIG_KEY_0': f'http.https://{host}/.extraHeader',
            'GIT_CONFIG_VALUE_0': f'Authorization: Basic {basic}',
        })
    return env


def ls_remote_branches(url: str) -> tuple[list[str], str | None]:
    """Branch names straight from the git server — works on any host."""
    if urlparse(url or '').scheme not in ('http', 'https'):
        return [], 'Only http(s) repository URLs are supported.'
    try:
        result = subprocess.run(
            ['git', 'ls-remote', '--heads', '--', normalize_repo_url(url) + '.git'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30,
            env={**os.environ, **git_env(url)},
        )
    except subprocess.TimeoutExpired:
        return [], 'The git server did not answer in time.'
    if result.returncode != 0:
        err = result.stderr.lower()
        if 'authentication' in err or 'could not read username' in err:
            return [], 'Authentication failed — the repository may be private (add a token for this host in Admin → Settings).'
        return [], 'Repository not found or not reachable.'
    names = [line.split('refs/heads/', 1)[1] for line in result.stdout.splitlines() if 'refs/heads/' in line]
    return sorted(names), None


# ── Hosting APIs ─────────────────────────────────────────────────────────────

def api_base(url: str) -> str | None:
    host, _ = split_repo_url(url)
    kind = detect_provider(host)
    if kind == 'github':
        return 'https://api.github.com' if host == 'github.com' else f'https://{host}/api/v3'
    if kind == 'gitlab':
        return f'https://{host}/api/v4'
    if kind == 'gitea':
        return f'https://{host}/api/v1'
    if kind == 'bitbucket':
        return 'https://api.bitbucket.org/2.0'
    return None


def api_headers(url: str, token: str = None) -> dict:
    host, _ = split_repo_url(url)
    kind = detect_provider(host)
    token = token or get_host_token(host)
    headers = {'Accept': 'application/vnd.github+json'} if kind == 'github' else {}
    if token:
        if kind == 'gitlab':
            headers['PRIVATE-TOKEN'] = token
        elif kind == 'gitea':
            headers['Authorization'] = f'token {token}'
        else:
            headers['Authorization'] = f'Bearer {token}'
    return headers


def repo_api_url(url: str) -> str | None:
    """API URL of the repository itself, or None for a plain git host."""
    base = api_base(url)
    if not base:
        return None
    _, path = split_repo_url(url)
    if detect_provider(url) == 'gitlab':
        return f'{base}/projects/{quote(path, safe="")}'
    if detect_provider(url) == 'bitbucket':
        return f'{base}/repositories/{path}'
    return f'{base}/repos/{path}'


def api_get(url: str, sub: str = '', params=None, timeout: int = 8, token: str = None):
    """GET on the repo's API (+ sub path). None when the host has no API or
    the request could not be sent. *token* overrides the host's configured one."""
    repo_url = repo_api_url(url)
    if not repo_url:
        return None
    try:
        return requests.get(f'{repo_url}{sub}', headers=api_headers(url, token), params=params, timeout=timeout)
    except requests.RequestException:
        return None


def api_error_message(url: str, response) -> str:
    """Clear message for a failed API call — never the raw body (GitHub's
    rate-limit body includes the caller's own IP address)."""
    label = PROVIDER_LABELS[detect_provider(url)]
    if response is None:
        return f'Could not reach {label}.'
    if response.status_code == 401:
        return f'The {label} token was rejected (401) — it is invalid or revoked. Update it in Admin → Settings.'
    if response.status_code == 404:
        return 'Repository not found, or the token can\'t see it (private repo?).'
    if response.status_code in (403, 429):
        return f'{label} API rate limit reached or access refused — try again later, or configure a token in Admin → Settings.'
    return f'{label} API returned an unexpected status ({response.status_code}).'


def _normalize_metadata(kind: str, data: dict) -> dict:
    """Map a hosting API's repo payload onto the GitHub-shaped dict the rest
    of the app (rule formats' parse_metadata, the repo info card) reads."""
    if kind == 'gitlab':
        ns = data.get('namespace') or {}
        lic = data.get('license') or {}
        return {
            'id': data.get('id'), 'name': data.get('path') or data.get('name'),
            'full_name': data.get('path_with_namespace'),
            'private': data.get('visibility') == 'private',
            'author': ns.get('path') or ns.get('name'), 'author_url': ns.get('web_url'),
            'author_avatar': ns.get('avatar_url') or data.get('avatar_url'),
            'repo_url': data.get('web_url'), 'api_url': None,
            'description': data.get('description'), 'homepage': None, 'language': None,
            'topics': data.get('topics') or data.get('tag_list') or [],
            'created_at': data.get('created_at'), 'updated_at': data.get('last_activity_at'),
            'pushed_at': data.get('last_activity_at'),
            'license': lic.get('key', '').upper() or None, 'license_name': lic.get('name'),
            'stars': data.get('star_count', 0), 'watchers': data.get('star_count', 0),
            'forks': data.get('forks_count', 0), 'open_issues': data.get('open_issues_count', 0),
            'default_branch': data.get('default_branch'), 'visibility': data.get('visibility'),
            'archived': data.get('archived', False), 'disabled': False,
        }
    if kind == 'bitbucket':
        owner = data.get('owner') or {}
        return {
            'id': data.get('uuid'), 'name': data.get('slug') or data.get('name'),
            'full_name': data.get('full_name'), 'private': data.get('is_private', False),
            'author': owner.get('nickname') or owner.get('display_name'),
            'author_url': ((owner.get('links') or {}).get('html') or {}).get('href'),
            'author_avatar': ((owner.get('links') or {}).get('avatar') or {}).get('href'),
            'repo_url': ((data.get('links') or {}).get('html') or {}).get('href'), 'api_url': None,
            'description': data.get('description'), 'homepage': data.get('website'),
            'language': data.get('language'), 'topics': [],
            'created_at': data.get('created_on'), 'updated_at': data.get('updated_on'),
            'pushed_at': data.get('updated_on'), 'license': None, 'license_name': None,
            'stars': 0, 'watchers': 0, 'forks': 0, 'open_issues': 0,
            'default_branch': (data.get('mainbranch') or {}).get('name'),
            'visibility': 'private' if data.get('is_private') else 'public',
            'archived': False, 'disabled': False,
        }
    # GitHub, and Gitea / Forgejo whose API mirrors GitHub's field names.
    owner = data.get('owner') or {}
    lic = data.get('license') or {}
    return {
        'id': data.get('id'), 'name': data.get('name'), 'full_name': data.get('full_name'),
        'private': data.get('private', False),
        'author': owner.get('login'), 'author_url': owner.get('html_url'),
        'author_avatar': owner.get('avatar_url'),
        'repo_url': data.get('html_url'), 'api_url': data.get('url'),
        'description': data.get('description'), 'homepage': data.get('homepage') or data.get('website'),
        'language': data.get('language'), 'topics': data.get('topics', []),
        'created_at': data.get('created_at'), 'updated_at': data.get('updated_at'),
        'pushed_at': data.get('pushed_at') or data.get('updated_at'),
        'license': lic.get('spdx_id'), 'license_name': lic.get('name'),
        'stars': data.get('stargazers_count', data.get('stars_count', 0)),
        'watchers': data.get('watchers_count', 0),
        'forks': data.get('forks_count', 0), 'open_issues': data.get('open_issues_count', 0),
        'default_branch': data.get('default_branch'), 'visibility': data.get('visibility'),
        'archived': data.get('archived', False), 'disabled': data.get('disabled', False),
        'size_kb': data.get('size', 0),
    }


def fallback_metadata(url: str, selected_license: str = None, user=None) -> dict:
    """Same shape as _normalize_metadata(), filled locally — for a plain git
    host, or when the hosting API can't be reached."""
    _, path = split_repo_url(url)
    return {
        'id': None, 'name': path.split('/')[-1] if path else None, 'full_name': path or None,
        'private': None,
        'author': repo_owner(url) or getattr(user, 'first_name', None) or 'Unknown',
        'author_url': None, 'author_avatar': None,
        'repo_url': normalize_repo_url(url), 'api_url': None,
        'description': None, 'homepage': None, 'language': None, 'topics': [],
        'created_at': None, 'updated_at': None, 'pushed_at': None,
        'license': selected_license, 'license_name': selected_license,
        'stars': 0, 'watchers': 0, 'forks': 0, 'open_issues': 0,
        'default_branch': None, 'visibility': None, 'archived': False, 'disabled': False,
    }


def repo_metadata(url: str, selected_license: str = None, user=None) -> dict:
    """Repository metadata from its host's API, falling back to what the URL
    itself tells (owner, name) when there is no API or it fails. A license
    the user picked explicitly always wins over the detected one."""
    resp = api_get(url)
    if resp is not None and resp.status_code == 200:
        meta = _normalize_metadata(detect_provider(url), resp.json())
    else:
        meta = fallback_metadata(url, selected_license, user)
    if selected_license:
        meta['license'] = meta['license_name'] = selected_license
    return meta


def check_accessible(url: str) -> tuple[bool, str]:
    """(ok, message). API check where there is one, `git ls-remote` else."""
    resp = api_get(url, timeout=5)
    if resp is not None:
        if resp.status_code == 200:
            return True, ''
        if resp.status_code in (401, 404):
            return False, api_error_message(url, resp)
    branches, err = ls_remote_branches(url)
    return (err is None), (err or '')


def list_branches(url: str) -> tuple[list[str], str | None]:
    """(branch names, error). Uses `git ls-remote`, which works on every host
    and costs no API quota."""
    return ls_remote_branches(url)


def default_branch(url: str) -> str | None:
    meta = repo_metadata(url)
    if meta.get('default_branch'):
        return meta['default_branch']
    try:
        result = subprocess.run(
            ['git', 'ls-remote', '--symref', '--', normalize_repo_url(url) + '.git', 'HEAD'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30,
            env={**os.environ, **git_env(url)},
        )
        m = re.search(r'^ref: refs/heads/(\S+)\s+HEAD', result.stdout, re.M)
        return m.group(1) if m else None
    except subprocess.TimeoutExpired:
        return None


def check_push_access(url: str, token: str) -> tuple[bool, str, dict | None]:
    """Can *token* push to *url*? (ok, message, repo metadata or None).
    Uses the host's API where there is one; on a plain git host only read
    access can be checked (`git ls-remote`), push is then assumed."""
    kind = detect_provider(url)
    label = PROVIDER_LABELS[kind]
    if kind == 'generic':
        host, _ = split_repo_url(url)
        env = {**os.environ, 'GIT_TERMINAL_PROMPT': '0'}
        try:
            r = subprocess.run(['git', 'ls-remote', '--heads', '--', authed_remote_url(url, token)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30, env=env)
        except subprocess.TimeoutExpired:
            return False, f'{host} did not answer in time.', None
        if r.returncode != 0:
            return False, 'The git server refused the token, or the repository does not exist.', None
        return True, 'Repository reachable (push access can only be checked by the first sync on a plain git host).', fallback_metadata(url)

    resp = api_get(url, token=token, timeout=10)
    if resp is None:
        return False, f'Network error reaching {label}.', None
    if resp.status_code != 200:
        return False, api_error_message(url, resp), None
    data = resp.json()
    meta = _normalize_metadata(kind, data)
    if kind == 'gitlab':
        perms = data.get('permissions') or {}
        level = max((perms.get('project_access') or {}).get('access_level', 0),
                    (perms.get('group_access') or {}).get('access_level', 0))
        can_push = level >= 30  # Developer
    elif kind == 'bitbucket':
        can_push = True  # Bitbucket's repo payload carries no permission field
    else:
        can_push = bool((data.get('permissions') or {}).get('push'))
    meta['has_push_access'] = can_push
    if not can_push:
        return False, "Token can see the repository but doesn't have write (push) access to it.", meta
    return True, '', meta


def repo_live_info(url: str) -> dict:
    """Data for the repository info card: {'provider', 'repo', 'repo_error',
    'commits', 'branches', 'contributors'} — repo/commits/branches/
    contributors in GitHub's shape whatever the host, so one card renders
    them all. Each part fails independently."""
    kind = detect_provider(url)
    info = {'provider': kind, 'provider_label': PROVIDER_LABELS[kind],
            'repo': None, 'repo_error': None, 'commits': [], 'branches': [], 'contributors': []}

    if kind == 'generic':
        return _live_info_from_git(url, info)

    resp = api_get(url)
    if resp is not None and resp.status_code == 200:
        raw = resp.json()
        info['repo'] = raw if kind in ('github', 'gitea') else _github_shaped_repo(_normalize_metadata(kind, raw))
    else:
        info['repo_error'] = api_error_message(url, resp)

    if kind == 'gitlab':
        commits = api_get(url, '/repository/commits', {'per_page': 10})
        branches = api_get(url, '/repository/branches', {'per_page': 50})
        people = api_get(url, '/repository/contributors', {'per_page': 20})
        if commits is not None and commits.status_code == 200:
            info['commits'] = [{
                'sha': c.get('id'), 'html_url': c.get('web_url'),
                'commit': {'message': c.get('message') or c.get('title'),
                           'author': {'name': c.get('author_name'), 'date': c.get('authored_date')}},
                'author': None,
            } for c in commits.json()]
        if branches is not None and branches.status_code == 200:
            info['branches'] = [{'name': b.get('name')} for b in branches.json()]
        if people is not None and people.status_code == 200:
            info['contributors'] = [{'login': p.get('name'), 'contributions': p.get('commits', 0),
                                     'avatar_url': None, 'html_url': None} for p in people.json()]
    elif kind == 'bitbucket':
        names, _ = ls_remote_branches(url)
        info['branches'] = [{'name': n} for n in names]
    else:  # github, gitea
        for key, sub, params in (('commits', '/commits', {'per_page': 10, 'limit': 10}),
                                 ('branches', '/branches', {'per_page': 50, 'limit': 50}),
                                 ('contributors', '/contributors', {'per_page': 20, 'anon': 'false'})):
            if kind == 'gitea' and key == 'contributors':
                continue  # Gitea has no contributors endpoint
            r = api_get(url, sub, params)
            if r is not None and r.status_code == 200:
                info[key] = r.json()
    if info['repo'] is None:
        return _live_info_from_git(url, info)
    return info


def _live_info_from_git(url: str, info: dict) -> dict:
    """No API answer (plain git host, private repo without a token, API
    switched off…): show what git itself tells — name, owner, branches —
    instead of an empty card. repo_error then only stays set when even git
    can't reach the repository."""
    api_error = info.get('repo_error')
    names, git_error = ls_remote_branches(url)
    if git_error:
        info['repo_error'] = git_error
        return info
    info['repo'] = _github_shaped_repo(fallback_metadata(url))
    info['repo']['default_branch'] = None
    if not info['branches']:
        info['branches'] = [{'name': n} for n in names]
    info['repo_error'] = None
    if api_error and detect_provider(url) != 'generic':
        host = split_repo_url(url)[0]
        info['repo_notice'] = (f'{api_error} Showing what git itself provides — add a token for '
                               f'{host} in Admin → Settings → Git Host Tokens for full details.')
    return info


def _github_shaped_repo(meta: dict) -> dict:
    return {
        'name': meta['name'], 'full_name': meta['full_name'], 'description': meta['description'],
        'html_url': meta['repo_url'], 'stargazers_count': meta['stars'], 'forks_count': meta['forks'],
        'watchers_count': meta['watchers'], 'open_issues_count': meta['open_issues'],
        'default_branch': meta['default_branch'], 'language': meta['language'],
        'topics': meta['topics'], 'created_at': meta['created_at'], 'updated_at': meta['updated_at'],
        'pushed_at': meta['pushed_at'], 'archived': meta['archived'], 'visibility': meta['visibility'],
        'license': {'spdx_id': meta['license'], 'name': meta['license_name']} if meta['license'] else None,
        'owner': {'login': meta['author'], 'html_url': meta['author_url'], 'avatar_url': meta['author_avatar']},
    }
