"""
social_links_core.py — a user's profile links (setting user.social_links: which networks, in which order,
their icon and the web hosts each accepts).

website / git / twitter / mastodon keep their own columns (website_url, github_url, twitter_url,
mastodon_url — used elsewhere); the other networks are stored together in User.social_links (JSON text).

    networks()                 the networks offered, from the setting
    user_links(user)           [{key, label, icon, url}] — what profile pages, the user list and UserChip show
    form_values(user)          {key: url} for the edit form
    clean_links(values)        ({key: url or None}, {key: error}) — http(s) only, the network's own hosts
    save_links(user, values)   store the cleaned values (no commit)
"""
from __future__ import annotations

import json
from urllib.parse import urlparse

from app.core.utils.app_settings import setting

SOCIAL_LINKS = setting('user.social_links')   # app/config/user.social_links.json
COLUMNS = {'website': 'website_url', 'git': 'github_url', 'twitter': 'twitter_url', 'mastodon': 'mastodon_url'}
MAX_LEN = 256


def networks() -> list:
    try:
        value = list(SOCIAL_LINKS.value or [])
    except Exception:
        value = []
    return [n for n in value if isinstance(n, dict) and n.get('key')]


def _stored(user) -> dict:
    try:
        data = json.loads(getattr(user, 'social_links', None) or '{}')
        return data if isinstance(data, dict) else {}
    except (TypeError, ValueError):
        return {}


def form_values(user) -> dict:
    stored = _stored(user)
    return {n['key']: (getattr(user, COLUMNS[n['key']], None) if n['key'] in COLUMNS else stored.get(n['key'])) or ''
            for n in networks()}


def user_links(user) -> list:
    out, stored = [], _stored(user)
    for n in networks():
        url = getattr(user, COLUMNS[n['key']], None) if n['key'] in COLUMNS else stored.get(n['key'])
        if url:
            icon = n.get('icon') or 'fa-solid fa-link'
            if n['key'] == 'git':                       # GitHub, GitLab, Gitea… their own logo
                try:
                    from app.features.rule.rule_format.utils_format.git_provider import PROVIDER_ICONS, detect_provider
                    icon = PROVIDER_ICONS.get(detect_provider(url), icon)
                except Exception:
                    pass
            out.append({'key': n['key'], 'label': n.get('label') or n['key'], 'icon': icon, 'url': url})
    return out


def _host_ok(host: str, hosts) -> bool:
    if not hosts:
        return True
    host = (host or '').lower()
    return any(host == h or host.endswith('.' + h) for h in hosts)


def clean_links(values: dict) -> tuple[dict, dict]:
    """Only the keys sent are returned: '' clears a link, an unknown network is ignored."""
    cleaned, errors = {}, {}
    known = {n['key']: n for n in networks()}
    for key, raw in (values or {}).items():
        if key not in known or not isinstance(raw, str):
            continue
        url = raw.strip()
        if not url:
            cleaned[key] = None
            continue
        p = urlparse(url)
        if p.scheme not in ('http', 'https') or not p.netloc or len(url) > MAX_LEN:
            errors[key] = f"{known[key].get('label', key)}: a web address (https://…, {MAX_LEN} characters at most)."
        elif not _host_ok(p.hostname, known[key].get('hosts')):
            errors[key] = f"{known[key].get('label', key)}: a link on {', '.join(known[key]['hosts'])}."
        else:
            cleaned[key] = url
    return cleaned, errors


def save_links(user, cleaned: dict) -> None:
    stored = _stored(user)
    for key, url in cleaned.items():
        if key in COLUMNS:
            setattr(user, COLUMNS[key], url)
        elif url:
            stored[key] = url
        else:
            stored.pop(key, None)
    user.social_links = json.dumps(stored) if stored else None
