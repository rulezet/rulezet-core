"""Resources of a rule (issue #77): Markdown notes and external links the rule's owner or an
admin attaches to it, shown on the rule's Resources tab.

Rights: everyone who can see the rule reads them; only the owner of the rule and admins add,
edit or delete. The content is user input shown to other people: links must be http(s), and the
page renders the Markdown through sanitize.js (renderMarkdown + hardenUserHtml: no images, no
same-site links, external links open in a new tab with noopener/noreferrer/nofollow) under a
warning that the content is not checked by Rulezet.
"""
import datetime
import re
import uuid as uuid_lib
from urllib.parse import urlparse

from app import db
from app.core.db_class.rule import RuleResource

KINDS = ('note', 'link', 'file')
# never accepted, whatever the setting says: programs and scripts (documents only)
BLOCKED_EXTENSIONS = {'py', 'pyc', 'sh', 'bash', 'zsh', 'ps1', 'psm1', 'bat', 'cmd', 'vbs', 'vbe', 'js', 'mjs', 'jse',
                      'wsf', 'hta', 'exe', 'dll', 'scr', 'msi', 'com', 'jar', 'php', 'pl', 'rb', 'lua', 'html', 'htm',
                      'svg', 'xhtml', 'lnk', 'iso', 'docm', 'xlsm', 'pptm', 'apk', 'elf', 'so', 'dylib'}
MAX_TITLE = 200
MAX_URL = 2000
MAX_NOTE = 50_000          # a note body
MAX_LINK_TEXT = 2_000      # a link's description
MAX_PER_RULE = 100


def config() -> dict:
    """Setting rule.resources (allowed file types, sizes, link preview)."""
    from app.core.utils.app_settings import get_setting
    try:
        value = get_setting('rule.resources') or {}
    except Exception:
        value = {}
    exts = [e for e in (str(x).lower().strip().lstrip('.') for x in value.get('file_extensions') or [])
            if e and e not in BLOCKED_EXTENSIONS]
    return {
        'file_extensions': exts,
        'max_file_bytes': int(value.get('max_file_kb') or 1024) * 1024,
        'max_pdf_bytes': int(value.get('max_pdf_kb') or 10240) * 1024,
        'max_total_bytes': int(value.get('max_total_kb') or 10240) * 1024,
        'link_preview': bool(value.get('link_preview', True)),
    }


def public_config() -> dict:
    """What the upload form needs to know."""
    c = config()
    return {'file_extensions': c['file_extensions'], 'max_file_bytes': c['max_file_bytes'],
            'max_pdf_bytes': c['max_pdf_bytes'],
            'max_total_bytes': c['max_total_bytes'], 'link_preview': c['link_preview']}


def _ext(name: str) -> str:
    return name.rsplit('.', 1)[-1].lower() if '.' in name else ''


def _clean_filename(name: str):
    """Base name only, no path, no control characters, 1-255 characters."""
    name = (name or '').replace('\\', '/').split('/')[-1]
    name = ''.join(c for c in name if c.isprintable()).strip().strip('.')
    return name[:255] if name else None


def files_size(rule_id: int, exclude_id: int = None) -> int:
    q = RuleResource.query.filter_by(rule_id=rule_id, kind='file')
    if exclude_id:
        q = q.filter(RuleResource.id != exclude_id)
    return sum(r.size or 0 for r in q.with_entities(RuleResource.size, RuleResource.id).all())


def can_manage(user, rule) -> bool:
    """Owner of the rule or admin."""
    return bool(user and getattr(user, 'is_authenticated', False) and rule
                and (user.id == rule.user_id or user.is_admin()))


def list_resources(rule_id: int) -> list:
    order = {'note': 0, 'file': 1, 'link': 2}
    rows = RuleResource.query.filter_by(rule_id=rule_id).order_by(RuleResource.created_at.desc()).all()
    return sorted(rows, key=lambda r: order.get(r.kind, 9))


def count_resources(rule_id: int) -> int:
    return RuleResource.query.filter_by(rule_id=rule_id).count()


def get_resource(rule_id: int, resource_id: int):
    return RuleResource.query.filter_by(rule_id=rule_id, id=resource_id).first()


def normalize_url(url: str) -> str:
    """'circl.lu' / 'www.circl.lu/path' → 'https://circl.lu…': an address typed without its
    scheme is a web link. Anything with another scheme (javascript:, data:, ftp:…) is kept as is
    and refused by _clean_url."""
    url = (url or '').strip()
    if url and not re.match(r'^[a-z][a-z0-9+-]*:', url, re.I):
        url = 'https://' + url.lstrip('/')
    return url


def _clean_url(url: str):
    url = normalize_url(url)
    if not url or len(url) > MAX_URL or any(c.isspace() for c in url):
        return None
    parsed = urlparse(url)
    host = parsed.hostname or ''
    if parsed.scheme not in ('http', 'https') or not host:
        return None
    if '.' not in host and host != 'localhost' and ':' not in host:   # 'foo' is not a site
        return None
    return url


def validate(data: dict, kind: str = None, rule_id: int = None, resource_id: int = None):
    """(clean fields, None) or (None, error message)."""
    kind = kind or (data.get('kind') or '').strip().lower()
    if kind not in KINDS:
        return None, 'Unknown resource type.'
    if kind == 'file':
        return _validate_file(data, rule_id, resource_id)
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()
    if not title and kind != 'link':          # a link without title takes the page's title, or its site
        return None, 'A title is required.'
    if len(title) > MAX_TITLE:
        return None, f'Title too long (max {MAX_TITLE} characters).'
    url = None
    if kind == 'link':
        url = _clean_url(data.get('url'))
        if not url:
            return None, 'Enter a web address, e.g. circl.lu or https://www.circl.lu/services/.'
        if len(content) > MAX_LINK_TEXT:
            return None, f'Description too long (max {MAX_LINK_TEXT} characters).'
    else:
        if not content:
            return None, 'The note is empty.'
        if len(content) > MAX_NOTE:
            return None, f'Note too long (max {MAX_NOTE} characters).'
    return {'kind': kind, 'title': title, 'url': url, 'content': content or None}, None


def _validate_file(data: dict, rule_id: int, resource_id: int = None):
    cfg = config()
    filename = _clean_filename(data.get('filename') or '')
    if not filename:
        return None, 'The file needs a name.'
    ext = _ext(filename)
    if ext not in cfg['file_extensions']:
        allowed = ', '.join('.' + e for e in cfg['file_extensions'])
        return None, f"'{filename}': this type of file can't be added (allowed: {allowed})."
    title = ((data.get('title') or '').strip() or filename)[:MAX_TITLE]
    if ext == 'pdf':
        return _validate_pdf(data, filename, title, cfg, rule_id, resource_id)
    content = data.get('content')
    if not isinstance(content, str):
        return None, f"'{filename}' is not a text file."
    if '\x00' in content:
        return None, f"'{filename}' looks like a binary file: only text files can be added."
    size = len(content.encode('utf-8'))
    if size == 0:
        return None, f"'{filename}' is empty."
    if size > cfg['max_file_bytes']:
        return None, f"'{filename}' is too large (max {cfg['max_file_bytes'] // 1024} KB)."
    if rule_id and files_size(rule_id, exclude_id=resource_id) + size > cfg['max_total_bytes']:
        return None, f"The files of this rule would be over {cfg['max_total_bytes'] // 1024} KB in total."
    return {'kind': 'file', 'title': title, 'url': None, 'content': content, 'data': None,
            'filename': filename, 'size': size}, None


def _validate_pdf(data, filename, title, cfg, rule_id, resource_id):
    """A PDF comes base64-encoded (content_b64) and must really be a PDF."""
    import base64
    import binascii
    raw = data.get('content_b64')
    if not isinstance(raw, str) or not raw:
        return None, f"'{filename}' is empty."
    if len(raw) > cfg['max_pdf_bytes'] * 4 // 3 + 16:
        return None, f"'{filename}' is too large (max {cfg['max_pdf_bytes'] // 1024} KB)."
    try:
        blob = base64.b64decode(raw.split(',', 1)[-1], validate=True)
    except (binascii.Error, ValueError):
        return None, f"'{filename}' could not be read."
    if not blob.startswith(b'%PDF-'):
        return None, f"'{filename}' is not a PDF file."
    size = len(blob)
    if size > cfg['max_pdf_bytes']:
        return None, f"'{filename}' is too large (max {cfg['max_pdf_bytes'] // 1024} KB)."
    if rule_id and files_size(rule_id, exclude_id=resource_id) + size > cfg['max_total_bytes']:
        return None, f"The files of this rule would be over {cfg['max_total_bytes'] // 1024} KB in total."
    return {'kind': 'file', 'title': title, 'url': None, 'content': None, 'data': blob,
            'filename': filename, 'size': size}, None


def _link_preview(url: str):
    if not config()['link_preview']:
        return None
    from app.core.utils.safe_fetch import page_preview
    return page_preview(url)


def create_resource(rule, user, data: dict):
    if count_resources(rule.id) >= MAX_PER_RULE:
        return None, f'A rule can have at most {MAX_PER_RULE} resources.'
    fields, error = validate(data, rule_id=rule.id)
    if error:
        return None, error
    if fields['kind'] == 'link':
        fields['preview'] = _link_preview(fields['url'])
        if not fields['title']:
            fields['title'] = ((fields['preview'] or {}).get('title') or urlparse(fields['url']).hostname or fields['url'])[:MAX_TITLE]
    res = RuleResource(uuid=str(uuid_lib.uuid4()), rule_id=rule.id, user_id=user.id, **fields)
    db.session.add(res)
    db.session.commit()
    return res, None


def update_resource(res, data: dict):
    if res.kind == 'file' and data.get('content') is None and data.get('content_b64') is None:   # rename only
        title = (data.get('title') or '').strip() or res.filename
        res.title = title[:MAX_TITLE]
        res.updated_at = datetime.datetime.now(datetime.timezone.utc)
        db.session.commit()
        return res, None
    fields, error = validate(data, kind=res.kind, rule_id=res.rule_id, resource_id=res.id)   # the type never changes
    if error:
        return None, error
    if res.kind == 'link' and fields['url'] != res.url:
        fields['preview'] = _link_preview(fields['url'])
    if res.kind == 'link' and not fields['title']:
        preview = fields.get('preview', res.preview) or {}
        fields['title'] = (preview.get('title') or urlparse(fields['url']).hostname or fields['url'])[:MAX_TITLE]
    for key, value in fields.items():
        if key != 'kind':
            setattr(res, key, value)
    res.updated_at = datetime.datetime.now(datetime.timezone.utc)
    db.session.commit()
    return res, None


def refresh_preview(res):
    """Read the link's page again."""
    from app.core.utils.safe_fetch import page_preview
    res.preview = page_preview(res.url) if res.kind == 'link' else None
    db.session.commit()
    return res


def delete_resource(res):
    db.session.delete(res)
    db.session.commit()
