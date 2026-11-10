"""third_party.py — the software Rulezet is built on, for the Third-Party Software page (/legal/third-party).

    python_packages()  every Python distribution installed in this instance's environment (direct
                       dependencies of pyproject.toml flagged), with its version, license and home page —
                       read from the packages' own metadata, so the list is always exact for this server
    other_components() everything else (front-end libraries, fonts, data sets, modules, system tools,
                       services), from the setting legal.third_party
"""
from __future__ import annotations

import functools
import importlib.metadata as md
import os
import re
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# license classifiers / long texts → a short name
_SHORT = [
    (r'apache', 'Apache 2.0'), (r'\bmpl\b|mozilla public', 'MPL 2.0'), (r'lgpl|lesser general', 'LGPL'),
    (r'(agpl|affero)[\s\S]{0,80}?(version 3|v3)', 'AGPL 3.0'), (r'agpl|affero', 'AGPL'),
    (r'\bgpl[\s\S]{0,60}?(version 3|v3)|gplv3', 'GPL 3.0'), (r'\bgpl|general public', 'GPL'), (r'bsd.?3|3.?clause|new bsd|modified bsd', 'BSD 3-Clause'),
    (r'bsd.?2|2.?clause|simplified bsd', 'BSD 2-Clause'), (r'\bbsd\b', 'BSD'), (r'\bmit\b', 'MIT'), (r'\bisc\b', 'ISC'),
    (r'python software foundation|\bpsf\b', 'PSF'), (r'unlicense', 'Unlicense'), (r'zope public', 'ZPL'),
    (r'historical permission|hpnd|mit-cmu', 'HPND'), (r'public domain', 'Public domain'),
]


# one name per license, whatever way each package spells it
_CANON = {
    'mit': 'MIT', 'mit license': 'MIT', 'expat': 'MIT',
    'apache-2.0': 'Apache 2.0', 'apache 2.0': 'Apache 2.0', 'apache software license': 'Apache 2.0',
    'apache license 2.0': 'Apache 2.0', 'apache license, version 2.0': 'Apache 2.0', 'apache 2': 'Apache 2.0',
    'bsd-3-clause': 'BSD 3-Clause', 'bsd 3-clause': 'BSD 3-Clause', 'new bsd license': 'BSD 3-Clause',
    'bsd-2-clause': 'BSD 2-Clause', 'bsd 2-clause': 'BSD 2-Clause', 'bsd license': 'BSD', 'bsd': 'BSD',
    'isc': 'ISC', 'isc license (iscl)': 'ISC', 'psf-2.0': 'PSF', 'python software foundation license': 'PSF',
    'mozilla public license 2.0 (mpl 2.0)': 'MPL 2.0', 'mpl-2.0': 'MPL 2.0',
    'gnu general public license v3 (gplv3)': 'GPL 3.0', 'gpl-3.0-only': 'GPL 3.0', 'gpl-3.0-or-later': 'GPL 3.0+',
    'gnu affero general public license v3': 'AGPL 3.0', 'agpl-3.0-only': 'AGPL 3.0', 'agpl-3.0-or-later': 'AGPL 3.0+',
    'gnu lesser general public license v2 or later (lgplv2+)': 'LGPL 2.0+', 'lgpl-2.1-only': 'LGPL 2.1',
    'lgpl-2.1-or-later': 'LGPL 2.1+', 'gnu lesser general public license v2 (lgplv2)': 'LGPL 2.0',
    'gnu lesser general public license v3 (lgplv3)': 'LGPL 3.0', 'lgpl-3.0-only': 'LGPL 3.0',
    'historical permission notice and disclaimer (hpnd)': 'HPND', 'mit-cmu': 'HPND (MIT-CMU)',
    'the unlicense (unlicense)': 'Unlicense', 'unlicense': 'Unlicense',
    'licenseref-nvidia-proprietary': 'NVIDIA proprietary (redistributable)',
    'licenseref-nvidia-software-license': 'NVIDIA proprietary (redistributable)',
    'isc license': 'ISC', 'mozilla public license 2.0': 'MPL 2.0', 'the unlicense': 'Unlicense',
    'gnu lesser general public license v3': 'LGPL 3.0', 'gnu general public license v3': 'GPL 3.0',
    'gnu lesser general public license v2': 'LGPL 2.0', 'gnu lesser general public license v2 or later': 'LGPL 2.0+',
    'historical permission notice and disclaimer': 'HPND', 'mit-0': 'MIT-0',
    'gplv3': 'GPL 3.0', '3-clause bsd license': 'BSD 3-Clause', 'lgpl-2.1-only': 'LGPL 2.1',
    'gnu library or lesser general public license': 'LGPL', 'other/proprietary license': 'Proprietary',
    'gnu general public license v2 or later': 'GPL 2.0+', 'mozilla public license 1.1': 'MPL 1.1',
    'nvidia proprietary software': 'NVIDIA proprietary (redistributable)',
}


def _canon(name: str) -> str:
    parts = re.split(r'\s+(OR|AND)\s+|\s+/\s+', name.strip())
    out = []
    for p in parts:
        if not p:
            continue
        if p in ('OR', 'AND'):
            out.append(p.lower())
            continue
        key = p.strip().lower()
        out.append(_CANON.get(key) or _CANON.get(re.sub(r'\s*\([^)]*\)\s*$', '', key)) or p.strip())
        out.append('/')
    text = ' '.join(out).rstrip('/ ').replace('or /', 'or').replace('and /', 'and').replace('/ or', 'or').replace('/ and', 'and')
    return text or name


def _license(meta) -> str:
    return _canon(_raw_license(meta))


# packages whose metadata carries no usable license (checked by hand against the project)
_KNOWN = {
    'cccs-yara': 'MIT',
    'cuda-toolkit': 'NVIDIA proprietary (redistributable)',
    'rulezet-editor': 'AGPL 3.0', 'rulezet-tester': 'AGPL 3.0', 'rulezet-validation': 'AGPL 3.0',
}


def _raw_license(meta) -> str:
    name = (meta.get('Name') or '').lower()
    if name in _KNOWN:
        return _KNOWN[name]
    expr = (meta.get('License-Expression') or '').strip()
    if expr:
        return expr
    text = (meta.get('License') or '').strip()
    classifiers = [c.split(' :: ')[-1] for c in (meta.get_all('Classifier') or []) if c.startswith('License ::')]
    specific = [c for c in classifiers if c not in ('OSI Approved', 'Other/Proprietary License')]
    if specific:
        return ' / '.join(dict.fromkeys(specific))
    if text and text.upper() != 'UNKNOWN' and len(text) <= 60 and '\n' not in text:
        return text                                     # e.g. 'LGPL-2.1-only' next to a bare 'OSI Approved'
    if classifiers:
        return ' / '.join(dict.fromkeys(classifiers))
    if text.upper() == 'UNKNOWN':
        text = ''
    if text and len(text) <= 40 and '\n' not in text:
        return text
    for pattern, name in _SHORT:
        if text and re.search(pattern, text, re.I):
            return name
    return 'See the project'


def _home(meta) -> str | None:
    for entry in meta.get_all('Project-URL') or []:
        label, _, url = entry.partition(',')
        if label.strip().lower() in ('homepage', 'home', 'source', 'repository', 'source code', 'github', 'code'):
            return url.strip()
    url = (meta.get('Home-page') or '').strip()
    if url.startswith('http'):
        return url
    for entry in meta.get_all('Project-URL') or []:
        url = entry.partition(',')[2].strip()
        if url.startswith('http'):
            return url
    return None


def _direct_dependencies() -> set[str]:
    try:
        with open(os.path.join(ROOT, 'pyproject.toml'), 'rb') as f:
            deps = tomllib.load(f).get('project', {}).get('dependencies', [])
    except (OSError, ValueError):
        return set()
    return {re.split(r'[\s<>=!~;\[]', d, 1)[0].lower().replace('_', '-') for d in deps}


@functools.lru_cache(maxsize=1)
def python_packages() -> list[dict]:
    direct = _direct_dependencies()
    seen, out = set(), []
    for dist in md.distributions():
        meta = dist.metadata
        name = meta.get('Name')
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        out.append({
            'name': name,
            'version': meta.get('Version') or '',
            'license': _license(meta),
            'url': _home(meta),
            'summary': (meta.get('Summary') or '').strip()[:140],
            'direct': name.lower().replace('_', '-') in direct,
        })
    out.sort(key=lambda p: (not p['direct'], p['name'].lower()))
    return out


def other_components() -> list[dict]:
    from app.core.utils.app_settings import get_setting
    try:
        groups = get_setting('legal.third_party') or []
    except Exception:
        groups = []
    return [g for g in groups if isinstance(g, dict) and g.get('items')]
