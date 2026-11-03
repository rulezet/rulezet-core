"""External checks of the Sigma editor — advice next to Rulezet's own validation (schema + pySigma,
editor_core.validate), which alone decides whether a rule can be saved:

  siem       pySigma backends (installed with Rulezet): the rule converted for each SIEM of the setting
             (a SIEM — Security Information and Event Management — is where a SOC searches its logs:
             Splunk SPL, Elasticsearch Lucene / ES|QL / EQL, Microsoft Sentinel & Defender KQL, Grafana
             Loki, Google SecOps…) — the query, or why it cannot be converted
  schemas    the same backends with their data-model pipelines (Splunk CIM, Elastic ECS, Microsoft
             Defender XDR, Sentinel ASIM, Azure Monitor): which fields of the rule each SIEM's own
             schema knows, under which name — a field it does not know means the rule finds nothing there
  pysigma    pySigma's own advice: its MEDIUM / LOW checks (Rulezet refuses only HIGH ones) — tags,
             wildcards instead of modifiers, numbers written as strings, all of them, duplicates…
  sigmahq    the conventions SigmaHQ's own repository enforces (tests/test_rules.py): title first, no
             one-value lists, no "ATT&CK" trademark in texts, Sysmon rules with an EventID, process
             creation through its category, valid regex escapes; and the file name SigmaHQ would give it
  sigmalint  sigmalint (MIT): findings by quality dimension (ATT&CK, taxonomy, false-positive risk,
             metadata, redundancy, style) and a score out of 100
  rsigma     rsigma lint (Rust, 91 checks of the Sigma 2.1 specification), when the binary is installed

Every tool is optional: missing → {"available": False, "reason": …}. Several rules (--- documents):
each one is checked on its own and the lines point into the whole document. Nothing is sent outside
the server: the converters and sigmalint work offline, rsigma gets Rulezet's local schema.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

from app.core.utils.app_settings import get_setting

MAX_TEXT = 200_000
TOOL_TIMEOUT = 10             # seconds per external program (sigmalint, rsigma) and per rule
TOOLS = ('siem', 'schemas', 'duplicates', 'cost', 'pysigma', 'sigmahq', 'sigmalint', 'rsigma')
# what the Checks panel shows for each tool (name, one line, link): the editor needs no list of its own
META = {
    'siem': {'name': 'SIEM conversion (pySigma)', 'url': 'https://github.com/SigmaHQ/pySigma',
             'about': 'The rule as a search query in each SIEM (the tool a SOC searches its logs with): Splunk, Elastic, Microsoft Sentinel / Defender, Loki, Google SecOps'},
    'schemas': {'name': 'SIEM data models', 'url': 'https://sigmahq-pysigma.readthedocs.io/en/latest/Processing_Pipelines.html',
                'about': "Does each SIEM's own schema know the rule's fields (Splunk CIM, Elastic ECS, Defender XDR, Sentinel ASIM, Azure Monitor)? An unknown field finds nothing there"},
    'duplicates': {'name': 'Already in Rulezet?', 'url': None,
                   'about': 'Sigma rules of this Rulezet with the same detection (same log source, fields and values, whatever their order or names) or a very close one'},
    'cost': {'name': 'Search cost', 'url': 'https://sigmahq.io/docs/basics/modifiers.html',
             'about': 'What makes the search slow or noisy in a SIEM (leading wildcards, unanchored regex, full-text keywords, huge lists, a condition that is only a negation), with an efficiency score'},
    'pysigma': {'name': 'pySigma advice', 'url': 'https://github.com/SigmaHQ/pySigma',
                'about': "pySigma's medium and low checks: what Rulezet accepts but could be written better"},
    'sigmahq': {'name': 'SigmaHQ conventions', 'url': 'https://github.com/SigmaHQ/sigma/blob/master/tests/test_rules.py',
                'about': 'What the SigmaHQ repository enforces on its rules, and the file name it would give'},
    'sigmalint': {'name': 'sigmalint', 'url': 'https://github.com/ni5h4nt/sigmalint',
                  'about': 'Quality score out of 100 (ATT&CK, taxonomy, false-positive risk, metadata, redundancy, style) and how to improve it'},
    'rsigma': {'name': 'rsigma lint', 'url': 'https://rsigma.io/cli/rule/lint/',
               'about': "The Sigma 2.1 specification's checks (rsigma, Rust)"},
}
LABELS = {
    'splunk': 'Splunk SPL', 'splunk_spl2': 'Splunk SPL2', 'lucene': 'Elasticsearch Lucene', 'esql': 'Elasticsearch ES|QL',
    'eql': 'Elastic EQL', 'elastalert': 'ElastAlert', 'kusto': 'Microsoft Sentinel / Defender (KQL)', 'loki': 'Grafana Loki (LogQL)',
    'secops': 'Google SecOps (YARA-L)', 'sumologic_cse': 'Sumo Logic CSE',
}
DEFAULT_TARGETS = ['splunk', 'lucene', 'esql', 'kusto', 'eql', 'loki', 'secops']
_SCHEMA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'rule', 'rule_format', 'schema_format', 'sigma_format.json')


def _conf():
    try:
        return get_setting('editor.external_checks') or {}
    except KeyError:
        return {}


def enabled_tools() -> list:
    """The Sigma tools switched on by the admin (setting editor.external_checks: sigma_<tool>)."""
    conf = _conf()
    return [t for t in TOOLS if conf.get(f'sigma_{t}', True)]


def run_checks(text: str, tools=None) -> dict:
    allowed = enabled_tools()
    wanted = [t for t in (tools or allowed) if t in allowed]
    if len(text or '') > MAX_TEXT:
        return {t: _unavailable(f'the document is larger than {MAX_TEXT // 1000} kB') for t in wanted}
    runners = {'siem': check_siem, 'schemas': check_schemas, 'duplicates': check_duplicates, 'cost': check_cost,
               'pysigma': check_pysigma, 'sigmahq': check_sigmahq,
               'sigmalint': check_sigmalint, 'rsigma': check_rsigma}
    docs = _documents(text or '')
    out = {}
    for tool in wanted:
        try:
            out[tool] = runners[tool](docs)
        except Exception as e:                     # a tool crashing never breaks the editor
            out[tool] = _unavailable(f'{tool} failed: {e}')
        out[tool]['meta'] = META[tool]
    return out


def _unavailable(reason):
    return {'available': False, 'reason': reason, 'ok': None, 'errors': [], 'warnings': []}


def _result(errors, warnings, infos=None, outputs=None, score=None):
    """A tool's answer (the editor's Checks panel contract, src/ui/checks.js): errors / warnings are
    remarks; infos are notes; outputs are things to read or copy (a query); score is { value, max, parts }."""
    out = {'available': True, 'ok': not errors, 'errors': errors, 'warnings': warnings}
    if infos:
        out['infos'] = infos
    if outputs:
        out['outputs'] = outputs
    if score:
        out['score'] = score
    return out


def _with_references(doc, data, others):
    """A correlation rule with the rules it names in front (the same document first, then Rulezet):
    what pySigma needs to convert it. Any other rule: itself."""
    corr = (data or {}).get('correlation')
    if not isinstance(corr, dict):
        return doc
    from app.features.rule.rule_format.available_format.sigma_format import SigmaRule
    texts = []
    for ref in corr.get('rules') or []:
        found = SigmaRule.find_referenced_rule(str(ref), others)
        if found and found not in texts:
            texts.append(found)
    return '\n---\n'.join(texts + [doc])


def _documents(text):
    """[(first_line, text, title)] — one per rule (YAML document)."""
    from rulezet_editor.validators import split_yaml_documents
    out = []
    for line, doc in split_yaml_documents(text):
        try:
            data = yaml.safe_load(doc)
        except Exception:
            data = None
        title = data.get('title') if isinstance(data, dict) else None
        out.append((line, doc, str(title or f'rule at line {line}'), data if isinstance(data, dict) else None))
    return out


def _line_of(doc, pattern, first_line, default=0):
    """The document line (in the whole text) of the first line matching `pattern`."""
    for i, line in enumerate(doc.splitlines()):
        if re.search(pattern, line):
            return first_line + i
    return first_line + default


# ── SIEM conversion (pySigma backends) ───────────────────────────────────────────

def check_siem(docs):
    try:
        from sigma.collection import SigmaCollection
        from sigma.plugins import InstalledSigmaPlugins
    except ImportError:
        return _unavailable('pySigma is not installed')
    backends = InstalledSigmaPlugins.autodiscover().backends
    targets = [t for t in (_conf().get('sigma_siem_targets') or DEFAULT_TARGETS) if t in backends]
    if not targets:
        return _unavailable('no pySigma backend installed for the targets of the setting')
    errors, warnings, outputs = [], [], []
    for line, doc, title, data in docs:
        source = _with_references(doc, data, [d for _, d, _, _ in docs if d is not doc])
        try:
            collection = SigmaCollection.from_yaml(source)
        except Exception as e:
            errors.append({'message': f'{title}: pySigma cannot read the rule ({e})', 'line': line, 'level': 'error'})
            continue
        for t in targets:
            label = LABELS.get(t, t)
            try:
                queries = backends[t]().convert(collection)
                if source is not doc:
                    queries = queries[-1:]       # a correlation: its own query (the rules it names come first)
                query = '\n'.join(q if isinstance(q, str) else json.dumps(q) for q in queries)
                n = len(queries)
                outputs.append({'label': label, 'ok': True, 'rule': title, 'line': line, 'text': query[:5000],
                                'detail': f"{n} quer{'ies' if n > 1 else 'y'} · {len(query)} characters · backend {t}"})
            except Exception as e:
                # red in the panel: this SIEM cannot run the rule as written
                outputs.append({'label': label, 'ok': False, 'rule': title, 'line': line, 'text': f'Cannot be converted: {str(e)[:500]}'})
    return _result(errors, warnings, outputs=outputs)


# ── SIEM data models (pySigma processing pipelines) ─────────────────────────────

# (backend, pipeline, label, products the pipeline is written for)
_SCHEMAS = [
    ('splunk', 'splunk_cim', 'Splunk CIM data model', ('windows',)),
    ('lucene', 'ecs_windows', 'Elastic Common Schema (Windows)', ('windows',)),
    ('lucene', 'ecs_macos_esf', 'Elastic Common Schema (macOS ESF)', ('macos',)),
    ('lucene', 'ecs_zeek_beats', 'Elastic Common Schema (Zeek)', ('zeek',)),
    ('kusto', 'microsoft_xdr', 'Microsoft Defender XDR tables', ('windows',)),
    ('kusto', 'sentinel_asim', 'Microsoft Sentinel ASIM', ('windows',)),
    ('kusto', 'azure_monitor', 'Azure Monitor (SecurityEvent)', ('windows',)),
    ('loki', 'loki_okta_system_log', 'Loki: Okta system log', ('okta',)),
]


def check_schemas(docs):
    try:
        from sigma.collection import SigmaCollection
        from sigma.plugins import InstalledSigmaPlugins
    except ImportError:
        return _unavailable('pySigma is not installed')
    plugins = InstalledSigmaPlugins.autodiscover()
    errors, warnings, infos, outputs = [], [], [], []
    for line, doc, title, data in docs:
        product = str(((data or {}).get('logsource') or {}).get('product') or '').lower() if isinstance((data or {}).get('logsource'), dict) else ''
        fits = [x for x in _SCHEMAS if product in x[3] and x[0] in plugins.backends and x[1] in plugins.pipelines]
        if not fits:
            infos.append({'message': f'No SIEM data model to check for product "{product or "—"}" (Windows, macOS, Zeek and Okta have some)',
                          'rule': title, 'line': line})
            continue
        try:
            SigmaCollection.from_yaml(doc)
        except Exception as e:                       # one clear reason, not a red line per SIEM
            errors.append({'message': f'{title}: pySigma cannot read the rule ({str(e)[:200]})', 'line': line, 'level': 'error'})
            continue
        for backend, pipeline, label, _ in fits:
            try:
                collection = SigmaCollection.from_yaml(doc)
                queries = plugins.backends[backend](processing_pipeline=plugins.pipelines[pipeline]()).convert(collection)
                mapping = _field_mapping(doc, plugins.pipelines[pipeline]())
                outputs.append({'label': label, 'ok': True, 'rule': title, 'line': line,
                                'detail': ' · '.join(f'{a} → {b}' if a != b else a for a, b in mapping) or 'no field',
                                'text': '\n'.join(q if isinstance(q, str) else json.dumps(q) for q in queries)[:5000]})
            except Exception as e:
                msg = str(e).split(' or the following')[0].split('. Please use')[0]
                outputs.append({'label': label, 'ok': False, 'rule': title, 'line': line,
                                'text': f'{msg[:400]}\n\nThis schema has no such field for this log source: the rule would find nothing '
                                        'there unless the field is added or renamed.'})
    return _result(errors, warnings, infos=infos, outputs=outputs)


def _field_mapping(doc, pipeline):
    """[(rule field, field in the SIEM's schema)], in the rule's order, each pair once."""
    from sigma.collection import SigmaCollection
    from sigma.rule import SigmaDetection

    def fields(rule):
        out = []

        def walk(d):
            for item in d.detection_items:
                if isinstance(item, SigmaDetection):
                    walk(item)
                elif item.field:
                    out.append(item.field)
        for d in rule.detection.detections.values():
            walk(d)
        return out
    rule = SigmaCollection.from_yaml(doc).rules[0]
    before = fields(rule)
    pipeline.apply(rule)
    return list(dict.fromkeys(zip(before, fields(rule))))


# ── Already in Rulezet? (same or very close detection) ───────────────────────────

_FP_CACHE = {}               # rule id -> (hash of its text, fingerprint, pairs): recomputed only when the text changes


def _pairs(data):
    """The rule's detection as a set of (field|modifiers, value), lower case — names of the search
    identifiers and order do not count — plus its log source."""
    det = data.get('detection') if isinstance(data.get('detection'), dict) else {}
    out = set()

    def add(sel):
        if isinstance(sel, dict):
            for k, v in sel.items():
                field = '|'.join([str(k).split('|')[0].lower()] + sorted(m.lower() for m in str(k).split('|')[1:]))
                for x in (v if isinstance(v, list) else [v]):
                    out.add((field, str(x).lower()))
        elif isinstance(sel, list):
            for x in sel:
                if isinstance(x, (dict, list)):
                    add(x)
                else:
                    out.add(('#keyword', str(x).lower()))
        elif sel is not None:
            out.add(('#keyword', str(sel).lower()))
    for name, sel in det.items():
        if name not in ('condition', 'timeframe'):
            add(sel)
    ls = data.get('logsource') if isinstance(data.get('logsource'), dict) else {}
    source = tuple(str(ls.get(k) or '').lower() for k in ('category', 'product', 'service'))
    return source, frozenset(out)


def _rulezet_fingerprints():
    import hashlib
    from app.core.db_class.rule import Rule
    from app.features.rule import rule_core as RuleModel
    try:
        loader = yaml.CSafeLoader
    except AttributeError:
        loader = yaml.SafeLoader
    rows = RuleModel._active().filter(Rule.format.ilike('sigma')).with_entities(
        Rule.id, Rule.title, Rule.uuid, Rule.original_uuid, Rule.to_string).all()
    seen = set()
    out = []
    for rid, title, uuid, original, text in rows:
        seen.add(rid)
        h = hashlib.sha1((text or '').encode('utf-8', 'replace')).hexdigest()
        cached = _FP_CACHE.get(rid)
        if not cached or cached[0] != h:
            try:
                data = yaml.load(text or '', Loader=loader)
            except Exception:
                data = None
            cached = (h, _pairs(data) if isinstance(data, dict) else None)
            _FP_CACHE[rid] = cached
        if cached[1]:
            out.append((rid, title, {str(uuid or '').lower(), str(original or '').lower()}, cached[1]))
    for rid in set(_FP_CACHE) - seen:           # deleted rules leave the cache
        _FP_CACHE.pop(rid, None)
    return out


def check_duplicates(docs):
    try:
        known = _rulezet_fingerprints()
    except Exception as e:
        return _unavailable(f'the rules of Rulezet cannot be read here ({e})')
    errors, warnings, infos = [], [], []
    for line, doc, title, data in docs:
        if data is None:
            continue
        source, pairs = _pairs(data)
        if not pairs:
            continue
        own = str(data.get('id') or '').lower()
        found = 0
        for rid, rtitle, ids, (rsource, rpairs) in known:
            link = f'/rule/detail_rule/{rid}'
            if own and own in ids:
                infos.append({'message': f'This is "{rtitle}" in Rulezet (same id)', 'rule': title, 'line': line, 'url': link})
                continue
            if rsource != source or not rpairs:
                continue
            common = len(pairs & rpairs) / len(pairs | rpairs)
            if common == 1:
                errors.append({'message': f'Same detection as "{rtitle}" (same log source, fields and values)', 'rule': title, 'line': line,
                               'url': link, 'detail': 'Publishing it would add a copy: improve that rule instead (an edit proposal), or make this one different.'})
                found += 1
            elif common >= 0.8:
                warnings.append({'message': f'Very close to "{rtitle}": {round(common * 100)} % of the fields and values in common', 'rule': title,
                                 'line': line, 'url': link, 'detail': 'Check it is not the same detection written another way.'})
                found += 1
            if found >= 10:
                break
        if not found:
            infos.append({'message': f'No Sigma rule of Rulezet has this detection ({len(known)} compared)', 'rule': title, 'line': line})
    return _result(errors, warnings, infos=infos)


# ── Search cost ──────────────────────────────────────────────────────────────────

def check_cost(docs):
    """Heuristics on what a SIEM must scan: each remark costs points of a 100 efficiency score."""
    errors, warnings, infos = [], [], []
    scores = []
    for line, doc, title, data in docs:
        if data is None:
            continue
        det = data.get('detection') if isinstance(data.get('detection'), dict) else {}
        penalty = 0

        def remark(points, message, pattern=None, detail=None, level='warning'):
            nonlocal penalty
            penalty += points
            item = {'message': message, 'rule': title, 'line': _line_of(doc, pattern, line) if pattern else line, 'detail': detail}
            item = {k: v for k, v in item.items() if v is not None}
            (warnings if level == 'warning' else infos).append(item)

        exact_somewhere = False
        for name, sel in det.items():
            if name in ('condition', 'timeframe'):
                continue
            if isinstance(sel, list) and all(not isinstance(x, (dict, list)) for x in sel):
                remark(25, f'{name}: full-text keywords — every field of every event is searched', rf'^\s*{re.escape(name)}\s*:',
                       'Name the field instead (e.g. CommandLine|contains) so the SIEM can use its index.')
                continue
            for item in (sel if isinstance(sel, list) else [sel]):
                if not isinstance(item, dict):
                    continue
                for key, value in item.items():
                    parts = str(key).split('|')
                    field, mods = parts[0], set(parts[1:])
                    values = value if isinstance(value, list) else [value]
                    pat = rf'^\s*-?\s*{re.escape(str(key))}\s*:'
                    if not mods - {'cased'} and not any(isinstance(v, str) and v.startswith('*') for v in values):
                        exact_somewhere = True
                    if 're' in mods:
                        for v in values:
                            v = str(v)
                            if not v.startswith('^') and not v.endswith('$'):
                                remark(10, f'{key}: unanchored regular expression — tried at every position of every value', pat,
                                       'Anchor it (^…$), or use contains / startswith / endswith: most SIEMs cannot index a regex.')
                                break
                            if v.startswith(('.*', '^.*')):
                                remark(8, f'{key}: regular expression starting with .*', pat, 'A leading .* is a full scan: drop it or use endswith.')
                                break
                    if 'contains' in mods or 'endswith' in mods:
                        short = [v for v in values if isinstance(v, str) and len(v.strip('*')) < 4]
                        if short:
                            remark(10, f'{key}: very short value "{short[0]}" with {"contains" if "contains" in mods else "endswith"} — slow and noisy', pat,
                                   'A few characters match a lot: use a longer, more specific value.')
                    if len(values) > 200:
                        remark(15, f'{key}: {len(values)} values in one list', pat, 'Very long OR lists are slow in most SIEMs: use a lookup / watchlist instead.')
                    elif len(values) > 50:
                        remark(5, f'{key}: {len(values)} values in one list', pat, 'Long OR lists slow the search down; consider a lookup table.', level='info')
                    if 'base64offset' in mods:
                        remark(3, f'{key}: base64offset searches each value 3 times (3 encodings)', pat, level='info')
                    if 'windash' in mods:
                        remark(2, f'{key}: windash searches each value in 5 dash variants', pat, level='info')
        if det and not exact_somewhere:
            remark(15, 'No exact value anywhere: only contains / endswith / regex — the SIEM cannot narrow the events down first', r'^detection\s*:',
                   'Add an exact field (an EventID, the Image or OriginalFileName, a service name) next to the fuzzy ones.')
        cond = det.get('condition') if isinstance(det.get('condition'), str) else ''
        if re.match(r'^\s*not\b', cond or '') and ' and ' not in cond and ' or ' not in cond:
            remark(30, 'The condition is only a negation: it matches almost every event', r'condition\s*:',
                   'Combine it with a selection: selection and not filter.')
        scores.append(max(0, 100 - penalty))
    score = {'value': round(sum(scores) / len(scores)), 'max': 100, 'parts': {}} if scores else None
    if score and len(scores) > 1:
        score['parts'] = {f'rule {i + 1}': v for i, v in enumerate(scores)}
    return _result(errors, warnings, infos=infos, score=score)


# ── pySigma's medium / low checks ────────────────────────────────────────────────

def check_pysigma(docs):
    try:
        from sigma.collection import SigmaCollection
        from sigma.validation import SigmaValidator
        from sigma.validators.base import SigmaValidationIssueSeverity
        from sigma.validators.core import validators
    except ImportError:
        return _unavailable('pySigma is not installed')
    errors, warnings, infos = [], [], []
    for line, doc, title, _ in docs:
        try:
            issues = SigmaValidator(validators=validators.values()).validate_rules(SigmaCollection.from_yaml(doc))
        except Exception:
            continue                                   # Rulezet's own check already says why
        for issue in issues:
            if issue.severity == SigmaValidationIssueSeverity.HIGH:
                continue                               # refused by Rulezet: shown in its own section
            detail = next((f'{a}: {getattr(issue, a)}' for a in ('tag', 'detection_name', 'detection_item', 'fieldname', 'identifier')
                           if getattr(issue, a, None) is not None), None)
            item = {'message': issue.description, 'rule': title, 'line': line, 'code': type(issue).__name__.replace('Issue', ''),
                    'detail': str(detail)[:300] if detail else None}
            item = {k: v for k, v in item.items() if v is not None}
            (warnings if issue.severity == SigmaValidationIssueSeverity.MEDIUM else infos).append(item)
    return _result(errors, warnings, infos=infos)


# ── SigmaHQ conventions (SigmaHQ/sigma tests/test_rules.py) ──────────────────────

_RE_ALLOWED = set('.*+?()[]{}|^$-/\\\'"AbBdDfnrsStvwWZ0123456789x')
_PREFIX = [   # (category | product | service) -> SigmaHQ file name prefix
    ('category', 'process_creation', 'proc_creation_'), ('category', 'image_load', 'image_load_'), ('category', 'file_event', 'file_event_'),
    ('category', 'registry_set', 'registry_set_'), ('category', 'registry_event', 'registry_event_'), ('category', 'registry_add', 'registry_add_'),
    ('category', 'registry_delete', 'registry_delete_'), ('category', 'network_connection', 'net_connection_'), ('category', 'dns_query', 'dns_query_'),
    ('category', 'process_access', 'proc_access_'), ('category', 'pipe_created', 'pipe_created_'), ('category', 'create_remote_thread', 'create_remote_thread_'),
    ('category', 'driver_load', 'driver_load_'), ('category', 'ps_script', 'posh_ps_'), ('category', 'ps_module', 'posh_pm_'),
    ('category', 'ps_classic_start', 'posh_pc_'), ('category', 'proxy', 'proxy_'), ('category', 'webserver', 'web_'), ('category', 'firewall', 'net_firewall_'),
    ('category', 'antivirus', 'av_'), ('category', 'file_delete', 'file_delete_'), ('category', 'file_access', 'file_access_'),
    ('product', 'aws', 'aws_'), ('product', 'azure', 'azure_'), ('product', 'gcp', 'gcp_'), ('product', 'm365', 'microsoft365_'),
    ('product', 'okta', 'okta_'), ('product', 'github', 'github_'), ('product', 'zeek', 'zeek_'),
    ('service', 'auditd', 'lnx_auditd_'), ('service', 'security', 'win_security_'), ('service', 'system', 'win_system_'),
    ('service', 'sysmon', 'sysmon_'), ('service', 'powershell', 'posh_'), ('service', 'application', 'win_app_'),
]
_OS_INFIX = {'windows': 'win_', 'linux': 'lnx_', 'macos': 'macos_'}


def _file_name(data):
    ls = data.get('logsource') if isinstance(data.get('logsource'), dict) else {}
    prefix = ''
    for key, value, p in _PREFIX:
        if str(ls.get(key) or '').lower() == value:
            prefix = p
            break
    if prefix and 'category' in ls and str(ls.get('product') or '').lower() in _OS_INFIX:
        prefix += _OS_INFIX[str(ls['product']).lower()]
    slug = re.sub(r'[^a-z0-9]+', '_', str(data.get('title') or 'rule').lower()).strip('_')
    return (prefix + slug)[:86].rstrip('_') + '.yml'


def _walk_re(node, depth=0):
    """(field, value) of every |re value in the detection (SigmaHQ looks 3 levels deep)."""
    if depth > 4:
        return
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(k, str) and '|re' in k:
                for x in (v if isinstance(v, list) else [v]):
                    if isinstance(x, str):
                        yield k, x
            else:
                yield from _walk_re(v, depth + 1)
    elif isinstance(node, list):
        for v in node:
            yield from _walk_re(v, depth + 1)


def check_sigmahq(docs):
    errors, warnings, infos = [], [], []
    for line, doc, title, data in docs:
        if data is None:
            continue
        w = lambda msg, pattern=None, detail=None, element=None: warnings.append(   # noqa: E731
            {k: v for k, v in {'message': msg, 'rule': title, 'line': _line_of(doc, pattern, line) if pattern else line,
                                'detail': detail, 'element': element}.items() if v is not None})
        if re.search(r'ATT&CK', doc):
            w('Do not write "ATT&CK" / "MITRE ATT&CK" in the rule (trademark): use the attack.* tags', r'ATT&CK',
              'SigmaHQ refuses rules whose text names the trademark.')
        if next(iter(data), None) != 'title':
            w('title must be the first key of the rule', None, 'SigmaHQ: the first top-level key is title.')
        if 'license' in data and not isinstance(data['license'], str):
            w('license must be a text (an SPDX id)', r'^license\s*:')
        det = data.get('detection') if isinstance(data.get('detection'), dict) else {}
        ls = data.get('logsource') if isinstance(data.get('logsource'), dict) else {}
        if "'source': 'eventlog'" in str(det).lower():
            w('source: eventlog is obsolete in a detection', r'source\s*:\s*eventlog')
        if str(ls.get('service') or '').lower() == 'sysmon' and not re.search(r'EventID\s*:', doc):
            w('A Sysmon rule (service: sysmon) needs an EventID in its detection, or a category instead', r'^logsource\s*:')
        if re.search(r'EventID\s*:\s*(1|4688)\s*$', doc, re.M) and re.search(r'Microsoft-Windows-(Security-Auditing|Sysmon)', str(det)):
            w('EventID 1 / 4688 with Provider_Name: use "category: process_creation" instead', r'EventID\s*:\s*(1|4688)\s*$')
        for name, sel in det.items():
            if name == 'condition':
                continue
            if isinstance(sel, list) and len(sel) == 1 and not isinstance(sel[0], str):
                w(f'{name}: a list with one item — write the item directly', rf'^\s*{re.escape(name)}\s*:')
            for item in (sel if isinstance(sel, list) else [sel]):
                if isinstance(item, dict):
                    for field, value in item.items():
                        if isinstance(value, list) and len(value) == 1:
                            w(f'{field}: a list with one value — write the value directly', rf'^\s*{re.escape(str(field))}\s*:',
                              'SigmaHQ: "Field: value" instead of a one-item list.')
        for field, value in _walk_re(det):
            bad = [value[i + 1] for i in range(len(value) - 1) if value[i] == '\\' and value[i + 1] not in _RE_ALLOWED and (i == 0 or value[i - 1] != '\\')]
            if bad:
                w(f'{field}: invalid escape \\{bad[0]} in the regular expression', re.escape(field))
        infos.append({'message': f'SigmaHQ file name: {_file_name(data)}', 'rule': title, 'line': line,
                      'detail': 'The name the SigmaHQ repository would give this rule (prefix from the log source, then the title).'})
    return _result(errors, warnings, infos=infos)


# ── sigmalint (quality score) ────────────────────────────────────────────────────

def _sigmalint_bin():
    local = os.path.join(os.path.dirname(sys.executable), 'sigmalint')
    return local if os.path.exists(local) else shutil.which('sigmalint')


def check_sigmalint(docs):
    exe = _sigmalint_bin()
    if not exe:
        return _unavailable('sigmalint is not installed (uv sync installs sigmalint-cli)')
    errors, warnings, infos, totals, parts = [], [], [], [], {}
    with tempfile.TemporaryDirectory(prefix='rz-sigmalint-') as tmp:
        paths = []
        for n, (line, doc, title, _) in enumerate(docs):
            path = os.path.join(tmp, f'rule_{n}.yml')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(doc)
            paths.append((path, line, title))
        if not paths:
            return _result([], [])
        # run in the empty temporary folder: no .sigmalintrc / filters of the server are read
        try:
            res = subprocess.run([exe, 'lint', '--format', 'json', *[os.path.basename(p) for p, _, _ in paths]],
                                 cwd=tmp, capture_output=True, text=True, timeout=TOOL_TIMEOUT * max(1, len(paths)))
        except subprocess.TimeoutExpired:
            return _unavailable('sigmalint took too long on this document')
        try:
            report = json.loads(res.stdout)
        except ValueError:
            return _unavailable(f'sigmalint gave no report ({(res.stderr or res.stdout).strip()[:200]})')
    by_file = {os.path.basename(p): (line, title) for p, line, title in paths}
    for f in report.get('files') or []:
        line, title = by_file.get(os.path.basename(f.get('path') or ''), (1, ''))
        for x in f.get('findings') or []:
            item = {'message': x.get('message') or '', 'rule': title, 'code': x.get('rule_id'),
                    'line': line + (x['line'] - 1 if x.get('line') else 0), 'detail': x.get('fix_hint') or None,
                    'level': {'error': 'error', 'warning': 'warning'}.get(x.get('severity'), 'info')}
            item = {k: v for k, v in item.items() if v is not None}
            {'error': errors, 'warning': warnings}.get(item['level'], infos).append(item)
        scores = f.get('scores')
        if scores:
            totals.append(scores.get('total', 0))
            for k, v in scores.items():
                if k != 'total':
                    parts.setdefault(k.replace('_', ' '), []).append(v)
    # several rules: their mean, as sigmalint's own summary
    score = {'value': round(sum(totals) / len(totals), 1), 'max': 100,
             'parts': {k: round(sum(v) / len(v), 1) for k, v in parts.items()}} if totals else None
    return _result(errors, warnings, infos=infos, score=score)


# ── rsigma lint ──────────────────────────────────────────────────────────────────

def _rsigma_bin():
    conf = _conf().get('sigma_rsigma_path')
    for cand in (conf, shutil.which('rsigma'), os.path.expanduser('~/.cargo/bin/rsigma')):
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None


def check_rsigma(docs):
    exe = _rsigma_bin()
    if not exe:
        return _unavailable('rsigma is not installed on the server (cargo install rsigma --locked, or a release binary in the PATH)')
    errors, warnings, infos = [], [], []
    with tempfile.TemporaryDirectory(prefix='rz-rsigma-') as tmp:
        for n, (line, doc, title, data) in enumerate(docs):
            if data is None:
                # rsigma 0.21 never returns on text that is not YAML: Rulezet's own check says why
                infos.append({'message': 'Not run on this rule: it is not valid YAML yet', 'rule': title, 'line': line})
                continue
            path = os.path.join(tmp, f'rule_{n}.yml')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(doc)
            # Rulezet's own copy of the Sigma schema: rsigma never downloads it
            cmd = [exe, 'rule', 'lint', '--output-format', 'ndjson', '--schema', _SCHEMA, path]
            try:
                res = subprocess.run(cmd, cwd=tmp, capture_output=True, text=True, timeout=TOOL_TIMEOUT)
            except subprocess.TimeoutExpired:
                infos.append({'message': f'rsigma took more than {TOOL_TIMEOUT} s on this rule: skipped', 'rule': title, 'line': line})
                continue
            if res.returncode not in (0, 1):
                return _unavailable(f'rsigma failed: {(res.stderr or res.stdout).strip()[:300]}')
            for raw in res.stdout.splitlines():
                try:
                    x = json.loads(raw)
                except ValueError:
                    continue
                sev = x.get('severity') or 'warning'
                item = {'message': x.get('message') or '', 'rule': title, 'code': x.get('rule'),
                        'line': line + (int(x['line']) - 1 if x.get('line') else 0), 'level': 'info' if sev in ('info', 'hint') else sev}
                {'error': errors, 'warning': warnings}.get(item['level'], infos).append(item)
    return _result(errors, warnings, infos=infos)
