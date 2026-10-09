import io
import os
import shutil
import uuid as _uuid
import datetime
import zipfile
from flask import current_app
from werkzeug.utils import secure_filename
from ... import db
from ...core.db_class.db import Workspace, WorkspaceRule, WorkspaceBundle, WorkspaceFile, Bundle, Rule


# ── Workspace documents (notes / imported text files) ──────────────────
# Documents are plain text stored in a Text column: only text formats are
# accepted, whatever the browser's file picker let through. The template
# shows these limits and the client checks them too, but this is the gate.
DOC_ALLOWED_EXTENSIONS = ('.md', '.markdown', '.txt', '.log', '.yaml', '.yml', '.json', '.csv', '.sh')
DOC_MAX_BYTES = 1024 * 1024          # 1 MB of UTF-8 text per document
DOC_TITLE_MAX = 200                  # WorkspaceDocument.title is String(200)


def _doc_extension(title: str) -> str:
    """'.md' for 'notes.md', '' for a name without extension."""
    dot = title.rfind('.')
    return title[dot:].lower() if dot > 0 else ''


def validate_document_fields(data: dict, partial: bool = False):
    """Check a document create/update payload.

    Returns (fields, error): `fields` holds the cleaned title/content to
    store (only the keys present when `partial`), `error` is a message for
    a 400 response, or None. Refuses non-text content (NUL bytes — what a
    binary file read as text produces), oversized content, and file names
    whose extension isn't a supported text format.
    """
    if not isinstance(data, dict):
        return None, 'Invalid request body.'
    fields = {}

    if 'title' in data or not partial:
        title = data.get('title', 'Untitled')
        if not isinstance(title, str) or not title.strip():
            return None, 'A file name is required.'
        title = title.strip()
        if len(title) > DOC_TITLE_MAX:
            return None, f'File name too long (max {DOC_TITLE_MAX} characters).'
        if '\x00' in title or '/' in title or '\\' in title:
            return None, 'Invalid characters in file name.'
        ext = _doc_extension(title)
        if ext and ext not in DOC_ALLOWED_EXTENSIONS:
            return None, (f'Unsupported file type "{ext}". Allowed: '
                          + ', '.join(DOC_ALLOWED_EXTENSIONS) + '.')
        fields['title'] = title

    if 'content' in data or not partial:
        content = data.get('content', '')
        if content is None:
            content = ''
        if not isinstance(content, str):
            return None, 'Document content must be text.'
        if '\x00' in content:
            return None, 'This file is not a text file (binary content). Only text documents can be imported.'
        if len(content.encode('utf-8', errors='replace')) > DOC_MAX_BYTES:
            return None, f'Document too large (max {DOC_MAX_BYTES // 1024} KB).'
        fields['content'] = content

    return fields, None


# ── Workspace files (images / PDF / office documents) ──────────────────
# Binary attachments, kept on disk outside static/. Whitelist only: the
# extension decides the type, the file's first bytes must match it (the
# browser-supplied MIME type is never trusted), and the MIME type we store
# and serve comes from this table. Not accepted, on purpose: video/audio,
# executables and scripts, HTML/SVG (can run script when opened), archives,
# and macro-enabled office files (.docm/.xlsm/… — and a .docx that hides a
# vbaProject.bin is refused too).
_OOXML = b'PK\x03\x04'
UPLOAD_ALLOWED_TYPES = {
    # ext:   (mime, magic-byte check)
    '.png':  ('image/png',  lambda b: b.startswith(b'\x89PNG\r\n\x1a\n')),
    '.jpg':  ('image/jpeg', lambda b: b.startswith(b'\xff\xd8\xff')),
    '.jpeg': ('image/jpeg', lambda b: b.startswith(b'\xff\xd8\xff')),
    '.gif':  ('image/gif',  lambda b: b[:6] in (b'GIF87a', b'GIF89a')),
    '.webp': ('image/webp', lambda b: b[:4] == b'RIFF' and b[8:12] == b'WEBP'),
    '.bmp':  ('image/bmp',  lambda b: b.startswith(b'BM')),
    '.pdf':  ('application/pdf', lambda b: b.startswith(b'%PDF-')),
    '.docx': ('application/vnd.openxmlformats-officedocument.wordprocessingml.document', lambda b: b.startswith(_OOXML)),
    '.xlsx': ('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', lambda b: b.startswith(_OOXML)),
    '.pptx': ('application/vnd.openxmlformats-officedocument.presentationml.presentation', lambda b: b.startswith(_OOXML)),
    '.odt':  ('application/vnd.oasis.opendocument.text', lambda b: b.startswith(_OOXML)),
    '.ods':  ('application/vnd.oasis.opendocument.spreadsheet', lambda b: b.startswith(_OOXML)),
    '.odp':  ('application/vnd.oasis.opendocument.presentation', lambda b: b.startswith(_OOXML)),
}
UPLOAD_MAX_BYTES = 10 * 1024 * 1024     # 10 MB per file
# Served inline (shown in the browser); everything else is a download.
UPLOAD_INLINE_MIME = {'image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/bmp', 'application/pdf'}


def _workspace_upload_dir(ws: Workspace) -> str:
    d = os.path.join(current_app.root_path, 'uploads', 'workspace', ws.uuid)
    os.makedirs(d, exist_ok=True)
    return d


def _has_macros(data: bytes) -> bool:
    """True if a zip-based office file carries VBA macros (or isn't a valid zip)."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            return any(n.lower().endswith('vbaproject.bin') or n.lower().startswith('basic/')
                       for n in zf.namelist())
    except zipfile.BadZipFile:
        return True


def validate_upload(filename: str, data: bytes):
    """Return (ext, mime, error) for an uploaded file — error is None when accepted."""
    name = secure_filename(filename or '')
    dot = name.rfind('.')
    ext = name[dot:].lower() if dot > 0 else ''
    if ext not in UPLOAD_ALLOWED_TYPES:
        return None, None, (f'File type "{ext or "no extension"}" is not allowed. Allowed: '
                            + ', '.join(UPLOAD_ALLOWED_TYPES) + '.')
    if not data:
        return None, None, 'The file is empty.'
    if len(data) > UPLOAD_MAX_BYTES:
        return None, None, f'File too large (max {UPLOAD_MAX_BYTES // (1024 * 1024)} MB).'
    mime, magic_ok = UPLOAD_ALLOWED_TYPES[ext]
    if not magic_ok(data[:16]):
        return None, None, f'The file content does not match its "{ext}" extension.'
    if data.startswith(_OOXML) and _has_macros(data):
        return None, None, 'Office files containing macros are not allowed.'
    return ext, mime, None


def save_workspace_file(ws: Workspace, filename: str, data: bytes, user_id: int):
    """Validate and store an uploaded file. Returns (WorkspaceFile, error)."""
    ext, mime, error = validate_upload(filename, data)
    if error:
        return None, error
    file_uuid = str(_uuid.uuid4())
    stored_name = file_uuid + ext
    with open(os.path.join(_workspace_upload_dir(ws), stored_name), 'wb') as fp:
        fp.write(data)
    original = (os.path.basename((filename or '').replace('\\', '/')).strip() or stored_name)[:255]
    wf = WorkspaceFile(uuid=file_uuid, workspace_id=ws.id, original_name=original,
                       stored_name=stored_name, mime_type=mime, size_bytes=len(data),
                       uploaded_by=user_id)
    db.session.add(wf)
    ws.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.commit()
    return wf, None


def get_workspace_files(ws: Workspace) -> list:
    return WorkspaceFile.query.filter_by(workspace_id=ws.id).order_by(WorkspaceFile.created_at.desc()).all()


def get_workspace_file(ws: Workspace, file_uuid: str):
    return WorkspaceFile.query.filter_by(workspace_id=ws.id, uuid=file_uuid).first()


def workspace_file_path(ws: Workspace, wf: WorkspaceFile) -> str:
    return os.path.join(_workspace_upload_dir(ws), wf.stored_name)


def delete_workspace_file(ws: Workspace, wf: WorkspaceFile):
    path = workspace_file_path(ws, wf)
    if os.path.exists(path):
        os.remove(path)
    db.session.delete(wf)
    db.session.commit()


def get_user_workspaces(user_id: int) -> list:
    return Workspace.query.filter_by(user_id=user_id).order_by(Workspace.name).all()


def get_all_workspaces() -> list:
    """Every workspace on the instance, regardless of owner — admin-only view."""
    return Workspace.query.order_by(Workspace.name).all()


def get_workspace_by_uuid(uuid_str: str):
    return Workspace.query.filter_by(uuid=uuid_str).first()


def create_workspace(user_id: int, name: str, description: str = None,
                     icon: str = 'fa-folder', color: str = '#0d6efd') -> Workspace:
    ws = Workspace(
        uuid=str(_uuid.uuid4()),
        name=name.strip(),
        description=description,
        icon=icon,
        color=color,
        user_id=user_id,
    )
    db.session.add(ws)
    db.session.commit()
    return ws


def update_workspace(ws: Workspace, name: str = None, description: str = None,
                     icon: str = None, color: str = None) -> Workspace:
    if name is not None:
        ws.name = name.strip()
    if description is not None:
        ws.description = description
    if icon is not None:
        ws.icon = icon
    if color is not None:
        ws.color = color
    ws.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.commit()
    return ws


def delete_workspace(ws: Workspace):
    upload_dir = os.path.join(current_app.root_path, 'uploads', 'workspace', ws.uuid)
    WorkspaceFile.query.filter_by(workspace_id=ws.id).delete()
    db.session.delete(ws)
    db.session.commit()
    shutil.rmtree(upload_dir, ignore_errors=True)


def add_rule_to_workspace(ws: Workspace, rule_id: int) -> bool:
    if WorkspaceRule.query.filter_by(workspace_id=ws.id, rule_id=rule_id).first():
        return False
    db.session.add(WorkspaceRule(workspace_id=ws.id, rule_id=rule_id))
    ws.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.commit()
    return True


def bulk_add_rules_to_workspace(ws: Workspace, rule_ids: list) -> int:
    added = 0
    for rid in rule_ids:
        if not WorkspaceRule.query.filter_by(workspace_id=ws.id, rule_id=rid).first():
            db.session.add(WorkspaceRule(workspace_id=ws.id, rule_id=rid))
            added += 1
    if added:
        ws.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
        db.session.commit()
    return added


def remove_rule_from_workspace(ws: Workspace, rule_id: int) -> bool:
    wr = WorkspaceRule.query.filter_by(workspace_id=ws.id, rule_id=rule_id).first()
    if not wr:
        return False
    db.session.delete(wr)
    ws.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.commit()
    return True


def get_workspace_rule_ids(ws: Workspace) -> list:
    """Active (non-deleted) rule ids currently in a workspace — feeds the
    "Export as Bundle" action."""
    return [
        rid for (rid,) in db.session.query(WorkspaceRule.rule_id)
        .join(Rule, Rule.id == WorkspaceRule.rule_id)
        .filter(WorkspaceRule.workspace_id == ws.id, Rule.is_deleted == False)
        .all()
    ]


# ── Bundles collected in a workspace ────────────────────────────────────────

def add_bundle_to_workspace(ws: Workspace, bundle_id: int, commit: bool = True) -> bool:
    if WorkspaceBundle.query.filter_by(workspace_id=ws.id, bundle_id=bundle_id).first():
        return False
    db.session.add(WorkspaceBundle(workspace_id=ws.id, bundle_id=bundle_id))
    ws.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    if commit:
        db.session.commit()
    return True


def remove_bundle_from_workspace(ws: Workspace, bundle_id: int) -> bool:
    """Drop the workspace ↔ bundle link. Also clears the "exported from this
    workspace" provenance so the bundle doesn't reappear. The bundle itself
    is never touched."""
    wb = WorkspaceBundle.query.filter_by(workspace_id=ws.id, bundle_id=bundle_id).first()
    bundle = Bundle.query.get(bundle_id)
    exported_here = bool(bundle and bundle.source_workspace_id == ws.id)
    if not wb and not exported_here:
        return False
    if wb:
        db.session.delete(wb)
    if exported_here:
        bundle.source_workspace_id = None
    ws.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.commit()
    return True


def get_workspace_bundle_links(ws: Workspace) -> list:
    """(WorkspaceBundle, Bundle) pairs, newest first."""
    return (
        db.session.query(WorkspaceBundle, Bundle)
        .join(Bundle, Bundle.id == WorkspaceBundle.bundle_id)
        .filter(WorkspaceBundle.workspace_id == ws.id)
        .order_by(WorkspaceBundle.added_at.desc())
        .all()
    )
