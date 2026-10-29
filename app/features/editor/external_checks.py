"""External checks of the YARA editor — an extra layer next to Rulezet's own validation, never a
replacement: Rulezet's syntax check (editor_core.validate_rule_syntax, yara-python) still decides
whether a rule can be saved. These tools only advise:

  yarax  YARA-X (VirusTotal, BSD-3): the new YARA engine's diagnostics — errors with line/column,
         warnings (always-true conditions, slow patterns…) — and its formatter
  cccs   CCCS YARA standard (Canadian Centre for Cyber Security, MIT): the meta section checked
         against the CCCS specification, and a version with the generated fields (id, fingerprint,
         version, dates…) and the meta sorted in the canonical order
  yaraqa yaraQA (Florian Roth, GPL-3.0, app/modules/yaraQA): logic and performance issues of the
         strings and the condition

Each tool is optional: missing package or submodule → {"available": False, "reason": …}. Which ones
run is the setting editor.external_checks. No tool may read a server file: YARA-X runs with includes
disabled, CCCS and yaraQA only parse the text (plyara), and nothing is ever sent outside.
"""
import importlib.util
import io
import os
import re
import sys
import tempfile

from app.core.utils.app_settings import get_setting

MAX_TEXT = 200_000            # a YARA document larger than this is not sent to the tools

TOOLS = ('yarax', 'cccs', 'yaraqa')
_LINE_COL = re.compile(r'--> line:(\d+):(\d+)')
_MODULES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'modules')


def enabled_tools() -> list:
    """The tools switched on by the admin (setting editor.external_checks)."""
    try:
        conf = get_setting('editor.external_checks') or {}
    except KeyError:
        conf = {}
    return [t for t in TOOLS if conf.get(t, True)]


def run_checks(text: str, tools=None) -> dict:
    """{tool: result} for the requested (and enabled) tools. A result: available, ok, errors[],
    warnings[] — each {message, line?, column?, code?, level?} — plus fixed_text when the tool offers
    a corrected / formatted version of the document."""
    allowed = enabled_tools()
    wanted = [t for t in (tools or allowed) if t in allowed]
    if len(text or '') > MAX_TEXT:
        return {t: _unavailable(f'the document is larger than {MAX_TEXT // 1000} kB') for t in wanted}
    runners = {'yarax': check_yarax, 'cccs': check_cccs, 'yaraqa': check_yaraqa}
    out = {}
    for tool in wanted:
        try:
            out[tool] = runners[tool](text or '')
        except Exception as e:                     # a tool crashing never breaks the editor
            out[tool] = _unavailable(f'{tool} failed: {e}')
    return out


def _unavailable(reason):
    return {'available': False, 'reason': reason, 'ok': None, 'errors': [], 'warnings': []}


def _result(errors, warnings, fixed_text=None):
    out = {'available': True, 'ok': not errors, 'errors': errors, 'warnings': warnings}
    if fixed_text is not None:
        out['fixed_text'] = fixed_text
    return out


# ── YARA-X ────────────────────────────────────────────────────────────────────────

def check_yarax(text: str) -> dict:
    try:
        import yara_x
    except ImportError:
        return _unavailable('yara-x is not installed (pip install yara-x)')
    compiler = yara_x.Compiler(includes_enabled=False)        # never read a file of the server
    errors = []
    try:
        compiler.add_source(text)
    except yara_x.CompileError as e:
        errors.append(_yarax_diag(str(e), 'error'))
    warnings = [{'message': w.get('title', ''), 'detail': w.get('text', ''), 'code': w.get('code'),
                 'line': w.get('line'), 'column': w.get('column'), 'level': 'warning'}
                for w in compiler.warnings()]
    fixed = None
    if not errors:
        out = io.BytesIO()
        yara_x.Formatter().format(io.BytesIO(text.encode('utf-8')), out)
        formatted = out.getvalue().decode('utf-8')
        fixed = formatted if formatted.strip() != text.strip() else None
    return _result(errors, warnings, fixed)


def _yarax_diag(raw: str, level: str) -> dict:
    first = raw.splitlines()[0] if raw else ''
    m = _LINE_COL.search(raw)
    code = re.match(r'(?:error|warning)\[(\w+)\]:', first)
    return {'message': re.sub(r'^(?:error|warning)\[\w+\]:\s*', '', first), 'detail': raw,
            'code': code.group(1) if code else None, 'level': level,
            'line': int(m.group(1)) if m else None, 'column': int(m.group(2)) if m else None}


# ── CCCS YARA standard ────────────────────────────────────────────────────────────

_INCLUDE_RE = re.compile(r'\binclude\s*"')     # anywhere (after a comment too); a string holding it only skips CCCS


def check_cccs(text: str) -> dict:
    # cccs-yara compiles with yara-python's defaults (includes on): a document with an include
    # would make it read a file of the server — never run it on one
    if _INCLUDE_RE.search(text):
        return _unavailable('documents with include are not checked (no file of the server is read)')
    # the MITRE ATT&CK data Rulezet already ships (submodule app/modules/cti), read by CCCS for the
    # mitre_att / actor fields — set before the package is imported (it reads it at import)
    cti = os.path.join(_MODULES_DIR, 'cti')
    if os.path.isdir(cti):
        os.environ.setdefault('MITRE_STIX_DATA_PATH', cti)
    try:
        from yara_validator.validator import run_yara_validator
    except ImportError:
        return _unavailable('cccs-yara is not installed (see requirements.txt)')
    with tempfile.NamedTemporaryFile('w', suffix='.yar', encoding='utf-8', delete=False) as fh:
        fh.write(text)
        path = fh.name
    try:
        processed = run_yara_validator(path, generate_values=True, check_import_modules=True)
    finally:
        os.unlink(path)
    errors, warnings, fixed_rules = [], [], []
    for rule in getattr(processed, 'yara_rules', []):
        res = rule.rule_return
        name = (rule.rule_plyara or {}).get('rule_name', '')
        errors += [_cccs_item(name, line.strip(), 'error')
                   for line in (res.return_errors() or '').splitlines() if line.strip()]
        warnings += [_cccs_item(name, line.strip(), 'warning')
                     for line in (res.return_warnings() or '').splitlines() if line.strip()]
        fixed_rules.append(res.return_validated_rule() or res.return_original_rule())
    if processed.return_file_error_state():
        # file-level problems (the document does not compile, bad encoding): {temp file name: message}
        for message in (getattr(processed, 'errors', None) or {}).values():
            message = str(message).replace(os.path.basename(path), 'document').replace('\t', ' ').strip()
            errors.append({'message': message, 'level': 'error'})
    fixed = '\n\n'.join(r.strip() for r in fixed_rules if r) + '\n' if fixed_rules else None
    return _result(errors, warnings, fixed if fixed and fixed.strip() != text.strip() else None)


_CCCS_SPEC = {}

# what to write for a missing field, when the specification has a short list of accepted values
_CCCS_EXAMPLE = {
    'status': 'TESTING', 'sharing': 'TLP:CLEAR', 'source': 'RULEZET', 'category': 'MALWARE', 'malware_type': 'DOWNLOADER',
    'author': 'you@example.org', 'description': 'What the rule detects', 'mitre_att': 'T1105',
    'date': '{today}', 'modified': '{today}', 'version': '1.0', 'report': 'TA26-0001', 'reference': 'https://example.org/report',
    'hash': '<sha256 of a sample>', 'actor_type': 'CRIMEWARE', 'malware': 'Family name', 'tool': 'Tool name',
}


def _cccs_spec():
    """{field: {description, format, optional, values}} from the CCCS specification shipped with the package."""
    if not _CCCS_SPEC:
        import yaml
        import yara_validator
        folder = os.path.dirname(yara_validator.__file__)
        with open(os.path.join(folder, 'CCCS_YARA.yml'), encoding='utf-8') as fh:
            fields = yaml.safe_load(fh) or {}
        with open(os.path.join(folder, 'CCCS_YARA_values.yml'), encoding='utf-8') as fh:
            values = yaml.safe_load(fh) or {}
        for key, conf in fields.items():
            if not isinstance(conf, dict) or key == 'values':
                continue
            arg = conf.get('argument') if isinstance(conf.get('argument'), dict) else {}
            accepted = [v.get('value') if isinstance(v, dict) else v for v in values.get(arg.get('valueName') or '', [])]
            for name in key.split('|'):
                _CCCS_SPEC[name] = {'description': conf.get('description', ''), 'format': conf.get('format', ''),
                                    'optional': conf.get('optional'), 'values': [str(v).replace('\\', '') for v in accepted if v]}
        if 'category' in _CCCS_SPEC:
            _CCCS_SPEC['category']['values'] = [str(v.get('value') if isinstance(v, dict) else v) for v in values.get('category_types', [])]
    return _CCCS_SPEC


def _cccs_item(rule, line, level):
    """A CCCS remark ("status: Missing required metadata") with what the specification says about
    the field: its purpose, format, accepted values, and a meta line to add."""
    import datetime
    field, _, message = line.partition(':')
    field = field.strip()
    item = {'rule': rule, 'message': line, 'level': level}
    try:
        spec = _cccs_spec().get(field)
    except Exception:
        spec = None
    if not spec or not message:
        return item
    parts = [spec['description'].strip().rstrip('.') + '.' if spec['description'] else '']
    if spec['values']:
        parts.append('Accepted values: ' + ', '.join(v.replace('|', ' | ') for v in spec['values'][:12])
                     + (' …' if len(spec['values']) > 12 else '') + '.')
    elif spec['format']:
        parts.append(f"Format: {spec['format']}.")
    if field == 'sharing':
        parts.append("Rulezet's tlp:clear tag is TLP:CLEAR here.")
    if field == 'category':
        parts.append('It needs a second field named after it, e.g. category = "MALWARE" with malware = "<family>" '
                     '(or tool, exploit, technique, info).')
    item['detail'] = ' '.join(p for p in parts if p)
    example = _CCCS_EXAMPLE.get(field) or (spec['values'][0].split('|')[0] if spec['values'] else None)
    if example and 'missing' in message.lower():
        example = example.replace('{today}', datetime.date.today().isoformat())
        item['element'] = f'{field} = "{example}"'
    return item


# ── yaraQA ────────────────────────────────────────────────────────────────────────

_YARAQA = {}


def _yaraqa_checks():
    """yaraQA's check functions, loaded from the submodule as a package of its own name (its folder
    is called "main"); the live performance test (slow, needs its sample data) is left out."""
    if 'mod' not in _YARAQA:
        pkg_dir = os.path.join(_MODULES_DIR, 'yaraQA', 'main')
        if not os.path.isfile(os.path.join(pkg_dir, 'core.py')):
            _YARAQA['mod'] = None
        else:
            spec = importlib.util.spec_from_file_location('yaraqa_main', os.path.join(pkg_dir, '__init__.py'),
                                                          submodule_search_locations=[pkg_dir])
            pkg = importlib.util.module_from_spec(spec)
            sys.modules['yaraqa_main'] = pkg
            spec.loader.exec_module(pkg)
            core = importlib.import_module('yaraqa_main.core')
            _YARAQA['mod'] = core
    return _YARAQA['mod']


def check_yaraqa(text: str) -> dict:
    core = _yaraqa_checks()
    if core is None:
        return _unavailable('yaraQA is not installed (git submodule app/modules/yaraQA)')
    import plyara
    rules = plyara.Plyara().parse_string(text)
    qa = core.YaraQA.__new__(core.YaraQA)        # no PerformanceTimer: no sample data loaded
    qa.initialize_regular_expressions()
    issues = []
    for rule in rules:
        issues += core.analyze_condition(qa, rule) + core.analyze_strings(qa, rule) + core.analyze_combinations(qa, rule)
    levels = {1: 'info', 2: 'warning', 3: 'error'}
    warnings = [{'rule': i.get('rule'), 'code': i.get('id'), 'message': i.get('issue', ''),
                 'detail': i.get('recommendation', ''), 'element': _short(i.get('element')),
                 'type': i.get('type'), 'level': levels.get(i.get('level'), 'warning')} for i in issues]
    # yaraQA advises — its level-3 findings are still shown as warnings: saving is Rulezet's decision
    return _result([], warnings)


def _short(element):
    if isinstance(element, dict):
        element = ', '.join(f'{k}: {v}' for k, v in element.items())
    text = str(element or '')
    return text if len(text) <= 160 else text[:159] + '…'
