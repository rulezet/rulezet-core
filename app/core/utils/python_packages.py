"""
python_packages.py — the command the app uses to install / upgrade / remove / list Python packages
in its own environment (AI provider SDKs, Admin › Settings › packages).

Rulezet's environment is made by uv (pyproject.toml + uv.lock → .venv/), and a uv environment has no
pip: `python -m pip` would fail. So: `uv pip … --python <this interpreter>` when uv is available,
else `python -m pip …` (an environment still made with pip). Same arguments either way.

    subprocess.run(pip_command('install', 'openai==1.107.1'), …)
"""
import os
import shutil
import sys


def _uv() -> str | None:
    found = shutil.which('uv')
    if found:
        return found
    home = os.path.expanduser('~/.local/bin/uv')        # where uv's installer puts it
    return home if os.path.isfile(home) and os.access(home, os.X_OK) else None


def pip_command(*args: str) -> list:
    """The full command for `pip <args>` against the running interpreter's environment."""
    uv = _uv()
    if uv:
        # uv pip: no --upgrade-strategy / -y / --disable-pip-version-check; uninstall never prompts
        cleaned = [a for a in args if a not in ('-y', '--yes', '--disable-pip-version-check')]
        return [uv, 'pip', *cleaned, '--python', sys.executable]
    return [sys.executable, '-m', 'pip', *args]


def install_hint(spec: str) -> str:
    """What to tell an admin to run by hand on the server."""
    return f'uv pip install {spec}' if _uv() else f'pip install {spec}'
