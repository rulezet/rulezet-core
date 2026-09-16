"""
deep_validate.py — Optional, opt-in "real engine" validation for Suricata
rules via suricata-language-server (SLS), on top of the always-on
grammar-only check (suricataparser) in suricata_format.py.

See docs/design/suricata_language_server_integration.md for the full
feasibility writeup this implements — in short: SLS shells out to a real
`suricata -T -v` run per call (~0.5-5s depending on hardware, confirmed by
live testing against this instance's own suricata 8.0.3), so this is never
run automatically on upload/import — only on-demand for one rule at a time
(rule detail page's "Deep validate" button), or as a slow, explicitly
admin-triggered background job over the whole corpus.

Suricata-only, deliberately never offered for Sagan: a genuine Sagan rule
(`alert any`/`alert syslog`, ...) is BY DEFINITION something a real
Suricata engine rejects, so "deep validating" a Sagan rule against real
Suricata semantics is meaningless — Sagan has no engine of its own to
validate against.
"""
import json
import subprocess
import tempfile
import os

from flask import current_app

# Real Suricata engine runs are on the order of hundreds of ms to a few
# seconds (engine boot dominates, not rule complexity — see the design doc)
# — generous enough for one rule to never look "hung" from a user's POV,
# tight enough that a wedged subprocess can't block a worker indefinitely.
DEFAULT_TIMEOUT_SECONDS = 20


def is_deep_validation_configured() -> bool:
    return bool(current_app.config.get('SURICATA_BINARY_PATH'))


def deep_validate_suricata_rule(content: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict:
    """Run one Suricata rule (or small buffer of rules) through a real
    Suricata engine via `suricata-language-server --batch-file
    --no-engine-analysis` (the --engine-analysis pass only ever runs AFTER
    the config-test pass already succeeded, so it's never what catches a
    syntax/protocol error — skipped here to keep this to one subprocess
    call, not two).

    Returns:
        {
            'available': bool,        # False if not configured or SLS isn't installed
            'error': str | None,      # human-readable reason when unavailable/failed
            'ok': bool | None,        # True/False once a real check ran, None if unavailable
            'diagnostics': [ {range, message, source, severity, content, sid}, ... ],
        }

    severity is the standard LSP scale: 1=Error, 2=Warning, 3=Information, 4=Hint.
    """
    binary_path = current_app.config.get('SURICATA_BINARY_PATH')
    if not binary_path:
        return {'available': False, 'error': 'Deep validation is not configured on this instance.',
                'ok': None, 'diagnostics': []}

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.rules', delete=False,
                                          encoding='utf-8') as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ['suricata-language-server', '--batch-file', tmp_path,
                 '--no-engine-analysis', '--suricata-binary', binary_path],
                capture_output=True, text=True, timeout=timeout,
            )
        except FileNotFoundError:
            return {'available': False,
                    'error': "'suricata-language-server' is not installed in this app's "
                             "environment (pip install suricata-language-server).",
                    'ok': None, 'diagnostics': []}
        except subprocess.TimeoutExpired:
            return {'available': True, 'error': f'Suricata engine check timed out after {timeout}s.',
                    'ok': None, 'diagnostics': []}

        diagnostics = []
        for line in (result.stdout or '').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                diagnostics.append(json.loads(line))
            except ValueError:
                continue  # a stray non-JSON line (e.g. a startup warning) — skip, don't fail the whole check

        # Exit code 0 unless at least one diagnostic is severity 1 (Error) —
        # mirrors SLS's own __init__.py batch-mode exit-code logic.
        ok = result.returncode == 0
        return {'available': True, 'error': None, 'ok': ok, 'diagnostics': diagnostics}
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
