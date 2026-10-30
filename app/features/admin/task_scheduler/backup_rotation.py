"""
backup_rotation.py — "Database backup + rotation" workflow task (job db_backup_rotate):

  1. a new backup with backup/scripts/backup_rulezet.sh (pg_dump, custom format);
  2. it is checked: the file exists, is not tiny, and pg_restore can read its table of contents;
  3. only then the oldest automatic backups are deleted so that `keep` remain (never below MIN_KEEP,
     never the one just made).
  Anything wrong → nothing is deleted, the job fails and every admin gets a notification.

Only automatic backups are rotated: files named rulezet_YYYY-MM-DD_HH-MM.dump, directly in
backup/dumps/ (no symlink, no sub-folder). Dumps named by hand (old.dump, before-x.dump…) are
never touched.
"""
import os
import re
import shutil
import subprocess

ROTATED = re.compile(r'^rulezet_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}\.dump$')
MIN_KEEP = 3                     # whatever is asked, at least this many backups stay
DEFAULT_KEEP = 10
MIN_DUMP_BYTES = 1024            # an empty / truncated dump is smaller than this
SCRIPT_TIMEOUT = 600


def backup_dir() -> str:
    return os.path.join(os.getcwd(), 'backup', 'dumps')


def _script() -> str:
    return os.path.join(os.getcwd(), 'backup', 'scripts', 'backup_rulezet.sh')


def list_backups() -> dict:
    """Every .dump in the folder: name, size, date, and whether rotation manages it."""
    folder = backup_dir()
    files = []
    if os.path.isdir(folder):
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            if not name.endswith('.dump') or os.path.islink(path) or not os.path.isfile(path):
                continue
            st = os.stat(path)
            files.append({'name': name, 'size': st.st_size, 'mtime': int(st.st_mtime),
                          'rotated': bool(ROTATED.match(name))})
    files.sort(key=lambda f: f['name'], reverse=True)
    try:
        free = shutil.disk_usage(folder if os.path.isdir(folder) else os.getcwd()).free
    except OSError:
        free = None
    return {'folder': folder, 'files': files, 'total': sum(f['size'] for f in files), 'disk_free': free,
            'min_keep': MIN_KEEP}


def _rotated_paths() -> list:
    """Automatic backups, oldest first (the name carries the date, so name order = date order)."""
    folder = os.path.realpath(backup_dir())
    out = []
    for f in sorted(list_backups()['files'], key=lambda f: f['name']):
        if not f['rotated']:
            continue
        path = os.path.realpath(os.path.join(folder, f['name']))
        if os.path.dirname(path) == folder:            # never outside the folder
            out.append((path, f['size']))
    return out


def check_dump(path: str) -> str | None:
    """None when the dump looks good, else what is wrong."""
    if not path or not os.path.isfile(path):
        return 'the new backup file is missing'
    if os.path.getsize(path) < MIN_DUMP_BYTES:
        return f'the new backup is only {os.path.getsize(path)} bytes'
    if shutil.which('pg_restore'):
        try:
            proc = subprocess.run(['pg_restore', '--list', path], capture_output=True, text=True, timeout=120)
        except (subprocess.TimeoutExpired, OSError) as e:
            return f'pg_restore could not read it: {e}'
        if proc.returncode != 0:
            return 'pg_restore cannot read it: ' + (proc.stderr or '').strip()[:300]
        if 'TABLE DATA' not in proc.stdout:
            return 'pg_restore reads it but finds no table data'
    return None


def make_backup(log) -> tuple:
    """Runs the backup script. (path, None) or (None, error)."""
    script = _script()
    if not os.path.exists(script):
        return None, f'backup script not found: {script}'
    before = {p for p, _ in _rotated_paths()}
    try:
        proc = subprocess.run(['bash', script], capture_output=True, text=True, timeout=SCRIPT_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, f'the backup took more than {SCRIPT_TIMEOUT // 60} minutes'
    except OSError as e:
        return None, f'could not run the backup script: {e}'
    for line in (proc.stdout or '').splitlines():
        if line.strip():
            log(line.strip(), 'info')
    if proc.returncode != 0:
        return None, f'pg_dump failed (exit {proc.returncode}): ' + (proc.stderr or '').strip()[:300]
    m = re.search(r'Backup saved to (\S+\.dump)', proc.stdout or '')
    path = os.path.realpath(m.group(1)) if m else None
    if not path:                                          # fall back on the new file in the folder
        new = [p for p, _ in _rotated_paths() if p not in before]
        path = new[-1] if new else None
    return path, None


def rotate(keep: int, newest: str, log) -> dict:
    """Deletes the oldest automatic backups beyond `keep` (≥ MIN_KEEP), never `newest`."""
    keep = max(MIN_KEEP, int(keep or DEFAULT_KEEP))
    paths = _rotated_paths()
    extra = len(paths) - keep
    deleted, freed = [], 0
    for path, size in paths[:max(0, extra)]:
        if path == newest or len(paths) - len(deleted) <= keep:
            continue
        try:
            os.remove(path)
            deleted.append(os.path.basename(path))
            freed += size
            log(f'Deleted the old backup {os.path.basename(path)} ({size / 1048576:.1f} MB)', 'info')
        except OSError as e:
            log(f'Could not delete {os.path.basename(path)}: {e}', 'warning')
    return {'kept': len(paths) - len(deleted), 'deleted': deleted, 'freed': freed}
