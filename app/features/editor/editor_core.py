"""Rule editor (app/modules/rulezet-editor) backed by this Rulezet: its validation and its
rules, called as Python functions. Never an HTTP call to rulezet.org.
See app/modules/rulezet-editor/docs/rulezet/ for what each editor feature uses here."""
import json
import re

import yara
from rulezet_editor import FunctionBackend

from app import db
from app.core.db_class.rule import Rule
from app.features.rule import rule_core as RuleModel
from app.features.rule_tester.sample_test_core import DbRunRegistry
from app.features.rule.rule_format.available_format.yara_format import (
    YaraRule, _condition_references, extract_undefined_identifier,
)


def validate(fmt, content):
    """The check a rule goes through on creation; YARA rules are compiled together with the
    Rulezet rules they reference. None for an unknown format (the editor shows nothing)."""
    return RuleModel.validate_rule_syntax(fmt, content, resolve_dependencies=True)


def _rule_item(rule):
    from flask_login import current_user
    return {
        'can_edit': _can_edit(current_user if current_user and current_user.is_authenticated else None, rule),
        'name': rule.title,
        'uuid': rule.uuid,
        'description': rule.description or '',
        'author': rule.author or '',
        'content': rule.to_string or '',
        'url': f'/rule/detail_rule/{rule.id}',
    }


def search_rules(fmt, query, limit):
    """Rules whose title contains the query (completion of rule names in conditions)."""
    q = RuleModel._active()
    if fmt:
        q = q.filter(Rule.format.ilike(fmt))
    if query:
        q = q.filter(Rule.title.ilike(f'%{query}%'))
    return [_rule_item(r) for r in q.order_by(Rule.title).limit(limit)]


def get_rule(fmt, name):
    """One rule by exact title (hover, "exists on Rulezet", Ctrl+Click)."""
    q = RuleModel._active().filter(Rule.title == name)
    if fmt:
        q = q.filter(Rule.format.ilike(fmt))
    rule = q.first()
    return _rule_item(rule) if rule else None


def fields(fmt):
    """Fields panel: Rulezet's fields for a rule of this format (setting editor.rule_fields)."""
    import copy
    from app.core.utils.app_settings import get_setting
    from app.features.rule.rule_format.utils_format.utils_import_update import get_licst_license
    per_format = get_setting('editor.rule_fields') or {}
    defs = copy.deepcopy(per_format.get((fmt or 'yara').lower()) or [])
    for d in defs:
        if d.get('options') == 'licenses':
            d['options'] = [{'value': lic, 'label': lic} for lic in get_licst_license()]
    return defs


def _tactics():
    from app.core.utils.app_settings import get_setting
    return get_setting('attack.tactics') or []


def _technique_item(t, tactics):
    """A technique as the Fields panel shows it: coloured by its first tactic (as AttackInput)."""
    first = next((x for x in tactics if x['key'] in (t.get('tactic_keys') or [])), None)
    return {'value': t['technique_id'], 'label': t['technique_id'], 'detail': t['name'],
            'color': first['color'] if first else None}


def _tag_item(t):
    """A tag as the tag picker shows it (its own colour)."""
    return {'value': t['id'], 'label': t['name'], 'color': t.get('color') or None}


def suggest(fmt, field, query, limit):
    """Autocompletion of the Fields panel, from Rulezet's own data (same sources as the manual form)."""
    if not query:
        return []
    if field == 'tags':
        from werkzeug.datastructures import MultiDict
        from app.features.tags import tags_core
        tags = tags_core.get_all_tags(MultiDict({'search': query, 'limit': str(limit), 'lean': '1'}))
        return [_tag_item(tags_core.picker_tag_json(t)) for t in tags[:limit]]
    if field == 'attack':
        from app.features.attack import attack_core
        tactics = _tactics()
        return [_technique_item(t, tactics) for t in attack_core.search_techniques(query, limit)]
    if field == 'related':
        rules = RuleModel._active().filter(Rule.title.ilike(f'%{query}%')).order_by(Rule.title).limit(limit)
        return [{'value': r.id, 'label': r.title, 'detail': f'{r.format} · {r.author or "?"}'} for r in rules]
    return []


def browse(fmt, field, path, page):
    """Folders of the Fields panel, one level at a time (same as the manual form's pickers):
    tags: Public / Private namespaces, then one page of a namespace;
    attack: the 14 tactics in matrix order, then the techniques of one tactic."""
    from werkzeug.datastructures import MultiDict
    if field == 'tags':
        from app.features.tags import tags_core
        if not path:
            groups = tags_core.picker_namespaces(MultiDict())
            return {'folders': [{'id': f'{group}\u001f{f["namespace"]}', 'label': f['namespace'] or '(no namespace)',
                                 'count': f['count'], 'group': group}
                                for group, folders in groups.items() for f in folders]}
        group, _, namespace = path[0].partition('\u001f')
        data = tags_core.picker_tags(MultiDict({'type': group, 'namespace': namespace, 'page': str(page), 'per_page': '50'}))
        return {'items': [_tag_item(t) for t in data['tags']], 'has_more': data['has_more']}
    if field == 'attack':
        from app.features.attack import attack_core
        tactics = _tactics()
        if not path:
            techniques = attack_core.get_all_techniques()
            count = {x['key']: 0 for x in tactics}
            for t in techniques:
                for k in t.get('tactic_keys') or []:
                    if k in count:
                        count[k] += 1
            return {'folders': [{'id': x['key'], 'label': x['label'], 'count': count[x['key']], 'color': x['color']}
                                for x in tactics]}
        return {'items': [_technique_item(t, tactics) for t in attack_core.get_all_techniques(path[0])]}
    return None


backend = FunctionBackend(name='Rulezet', validate=validate, search_rules=search_rules, get_rule=get_rule,
                          fields=fields, suggest=suggest, browse=browse)


def rule_dependencies(rule_id, user):
    """A YARA rule and every YARA rule it needs (transitively), the needed ones first, in the
    order they compile — what the edit page's YARA editor loads around the rule. Each one says
    whether `user` may edit it (owner or admin): only then can it be unlocked in the editor.
    None when the rule is missing, deleted or not YARA."""
    from app.features.rule_relation.rule_relation_core import dependency_install_order, get_dependency_graph
    rule = RuleModel.get_rule(rule_id)
    if not rule or (rule.format or '').lower() != 'yara':
        return None
    graph = get_dependency_graph(rule.id)
    wanted = [n['id'] for n in graph['nodes'] if n['role'] == 'requires' and (n['format'] or '').lower() == 'yara']
    found = {r.id: r for r in RuleModel._active().filter(Rule.id.in_(wanted))} if wanted else {}
    order = dependency_install_order([i for i in wanted if i in found], graph['edges'])
    item = lambda r: {**_rule_item(r), 'id': r.id, 'can_edit': _can_edit(user, r)}   # noqa: E731
    return {'rule': item(rule), 'dependencies': [item(found[i]) for i in order], 'truncated': graph['truncated']}


MAX_ACTIVE_RUNS_PER_USER = 2
MAX_ACTIVE_RUNS = 20


def _rulezet_test_service(*args, **kwargs):
    """rulezet-tester's TestService, plus: a finished run from the Test button is kept with the
    Rulezet rules it tested unchanged (sample_test_core.record_editor_run)."""
    from rulezet_tester import TestService

    class RulezetTestService(TestService):
        def start(self, fmt, text, set_ids, owner=None):
            # one user may not flood the sandbox: a few runs at a time each, a bounded queue overall
            from rulezet_tester import TestError
            from app.core.db_class.rule_tester import SampleTestRun
            import datetime
            # a run left 'running' by a restart must not block anyone: only recent ones count
            since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=30)
            active = SampleTestRun.query.filter(SampleTestRun.status.in_(('queued', 'running')),
                                                SampleTestRun.created_at >= since)
            if owner is not None and active.filter(SampleTestRun.user_id == owner).count() >= MAX_ACTIVE_RUNS_PER_USER:
                raise TestError('You already have tests running: wait for them to finish.')
            if active.count() >= MAX_ACTIVE_RUNS:
                raise TestError('The test sandbox is busy: try again in a minute.')
            return super().start(fmt, text, set_ids, owner=owner)

        def _execute(self, run_id, fmt, text, paths):
            super()._execute(run_id, fmt, text, paths)
            registry = self.registry
            try:
                with registry.app.app_context():
                    from app.features.rule_tester.sample_test_core import keep_document, record_editor_run
                    keep_document(run_id, text)
                    record_editor_run(registry.get(run_id), text)
            except Exception:                    # never let the bookkeeping break a test run
                pass

    return RulezetTestService(*args, **kwargs)


def _test_service():
    """Tests on samples (app/modules/rulezet-tester). Two modes:
      - lab VM (RULE_TESTS_LAB=rzlab@host): every run goes over SSH to the isolated lab, the only
        place real malware may live (see rulezet-tester docs/lab.md); nothing runs here;
      - local: the safe sets shipped with rulezet-tester plus RULE_TESTS_SAMPLES folders, isolated
        by RULE_TESTS_SANDBOX (bwrap by default: without bubblewrap the Test button does not show).
    None when switched off."""
    import os
    mode = os.environ.get('RULE_TESTS_SANDBOX', 'bwrap').strip().lower()
    if mode in ('', 'off', 'none', 'false'):
        return None
    try:
        from rulezet_tester import FolderSampleStore, RemoteLab, Sandbox, TestService
        from rulezet_tester.web import SAMPLES
    except ImportError:
        return None
    lab = os.environ.get('RULE_TESTS_LAB', '').strip()
    if lab:
        remote = RemoteLab(lab, key=os.environ.get('RULE_TESTS_LAB_KEY') or None,
                           known_hosts=os.environ.get('RULE_TESTS_LAB_KNOWN_HOSTS') or None)
        return _rulezet_test_service(remote, remote, registry=DbRunRegistry('editor'))
    extra = [d for d in os.environ.get('RULE_TESTS_SAMPLES', '').split(os.pathsep) if d.strip()]
    # sets read from this server's own folders (/usr/bin, documents, PE) show what is installed on it:
    # only when an admin allows it (setting editor.test_system_sets, off by default), read live
    def system_sets():
        from app.core.utils.app_settings import get_setting
        return bool(get_setting('editor.test_system_sets'))
    return _rulezet_test_service(FolderSampleStore(SAMPLES, *extra, system_sets=system_sets), Sandbox(mode=mode),
                                 registry=DbRunRegistry('editor'))


tests = _test_service()


def create_test_service():
    """Same samples and sandbox as the Test button, but the run executes right away in the
    calling thread (the Create job waits for it) and is recorded as origin 'create'."""
    if not tests:
        return None
    from rulezet_tester import TestService
    return TestService(tests.store, tests.sandbox, registry=DbRunRegistry('create'), executor=lambda fn: fn())


def test_document(plan, imports):
    """One YARA source with every rule of the plan, each after the rules it needs (rules taken
    from Rulezet first), the imports gathered at the top: what the Create job tests."""
    by_name = {e['name']: e for e in plan['rules']}
    modules = {m for m in imports or [] if re.fullmatch(r'\w+', str(m))}
    parts, done, rulezet_ids = [], set(), []

    def strip(text):
        modules.update(re.findall(r'^\s*import\s+"(\w+)"\s*$', text or '', flags=re.M))
        return re.sub(r'^\s*import\s+"[^"]+"\s*$', '', text or '', flags=re.M).strip()

    def add(e, stack=()):
        if e['name'] in done or e['name'] in stack:
            return
        for d in e.get('depends_on') or []:
            if d['where'] == 'document' and d['name'] in by_name:
                add(by_name[d['name']], stack + (e['name'],))
            elif d['where'] == 'rulezet' and d.get('id') not in rulezet_ids:
                rulezet_ids.append(d.get('id'))
        done.add(e['name'])
        parts.append(strip(e['text']))

    for e in plan['rules']:
        add(e)
    needed = {r.id: r for r in RuleModel._active().filter(Rule.id.in_([i for i in rulezet_ids if i]))} if rulezet_ids else {}
    head = [strip(needed[i].to_string) for i in rulezet_ids if i in needed]
    return ''.join(f'import "{m}"\n' for m in sorted(modules)) + '\n\n'.join(head + parts) + '\n'


# ── Several YARA rules at once: check each one, then create them ────────────────
#
# The editor sends the rules it parsed ({name, text}) and the document's imports. Nothing is
# trusted: every rule is compiled here, on its own with what it needs (other rules of the
# document, rules already in Rulezet, modules). A rule already in Rulezet with the same content
# is reused for the links; with a different content it is updated when the user may edit it
# (owner or admin), otherwise an edit proposal goes to its owner. Nothing is written while one
# rule has an error (no bad rule either): the editor shows the errors instead.
#
# Statuses: new, exists, update, proposal, error, blocked; after creation: created, updated, proposed.


MAX_RULES = 200
MAX_COMPILES = 60
_HEADER = re.compile(r'^\s*(?:(?:private|global)\s+)*rule\s+([A-Za-z_]\w*)')
_EMPTY_UUIDS = {'', 'unknown', 'none', 'null', 'n/a'}


class _Validation:
    """What YaraRule.parse_metadata reads from a validation result."""
    def __init__(self, content):
        self.normalized_content = content


def _meta_id(text):
    m = re.search(r'\b(?:id|uuid)\s*=\s*"([^"]+)"', text)
    return m.group(1).strip() if m else ''


def _rule_link(rule):
    return {'id': rule.id, 'title': rule.title, 'url': f'/rule/detail_rule/{rule.id}'}


def _existing(name, content, meta_id):
    """(rule, reason) when this rule is already in Rulezet."""
    if meta_id.lower() not in _EMPTY_UUIDS:
        rule = RuleModel._active().filter(
            db.or_(Rule.uuid == meta_id, Rule.original_uuid == meta_id)).first()
        if rule:
            return rule, 'same id'
    rule = RuleModel.get_rule_by_content(content)
    if rule:
        return rule, 'same content'
    rule = RuleModel._active().filter(Rule.format.ilike('yara'), Rule.corpus_identifier == name).first() \
        or RuleModel._active().filter(Rule.format.ilike('yara'), Rule.title == name).first()
    if rule:
        return rule, 'same rule name'
    return None, None


def _same_content(a, b):
    return ''.join((a or '').split()) == ''.join((b or '').split())


def _can_edit(user, rule):
    """Same rule as the edit page: the owner or an admin."""
    return bool(user) and (user.id == rule.user_id or user.is_admin())


PENDING = ('new', 'update', 'proposal')          # will be written once every check passes


def _rulezet_rule(name):
    return RuleModel._active().filter(Rule.format.ilike('yara'), Rule.title == name).first()


def _line_offset_error(message, prefix_lines):
    """Compiler messages count lines in the whole compiled source: bring them back to the rule."""
    m = re.match(r'line (\d+): (.*)', message)
    if not m:
        return {'message': message}
    line = int(m.group(1)) - prefix_lines
    if line < 1:
        return {'message': f'In a rule it needs: {m.group(2)}'}
    return {'message': m.group(2), 'line': line}


def _refusal(message):
    """add_rule_core's codes (DUPLICATE:uuid:id:title, ...) as a sentence."""
    message = str(message)
    for code, text in (('UUID_DUPLICATE:', 'A rule with this id already exists'),
                       ('DUPLICATE:', 'A rule with this content already exists'),
                       ('TRASH_CONFLICT:', 'The same rule is in the trash')):
        if message.startswith(code):
            parts = message.split(':', 3)
            return f'{text}: "{parts[3]}"' if len(parts) > 3 else text
    return message


# ── Fields panel values (rulezet-editor) -> the rule Rulezet creates ───────────────

_TEXT_FIELDS = ('title', 'description', 'author', 'license', 'version', 'source', 'original_uuid')
_LIST_FIELDS = ('cve', 'attack', 'tags')
_RELATION_KINDS = ('references', 'depends_on', 'related', 'variant_of', 'duplicate_of')


def clean_fields(raw):
    """The Fields panel's values for one rule, from the browser: known fields only, size-capped."""
    if not isinstance(raw, dict):
        return {}
    values = raw.get('values') if isinstance(raw.get('values'), dict) else raw
    out = {}
    for key in _TEXT_FIELDS:
        v = values.get(key)
        if isinstance(v, (str, int, float)) and str(v).strip():
            out[key] = str(v).strip()[:5000]
    for key in _LIST_FIELDS:
        items = values.get(key)
        if not isinstance(items, list):
            continue
        clean = []
        for item in items[:100]:
            v = item.get('value') if isinstance(item, dict) else item
            if isinstance(v, (str, int)) and str(v).strip():
                clean.append(str(v).strip()[:200])
        if clean:
            out[key] = clean
    related = values.get('related')
    if isinstance(related, list):
        links = []
        for item in related[:20]:
            if isinstance(item, dict) and str(item.get('value', '')).isdigit():
                kind = item.get('kind') if item.get('kind') in _RELATION_KINDS else 'references'
                links.append({'id': int(item['value']), 'kind': kind})
        if links:
            out['related'] = links
    return out


def apply_fields(rule_dict, fields):
    """What the user typed in the Fields panel wins over what parse_metadata read from the rule
    (the panel already shows the rule's own values when they exist)."""
    if not fields:
        return rule_dict
    for key in _TEXT_FIELDS:
        if fields.get(key):
            rule_dict[key] = fields[key]
    if fields.get('cve'):
        rule_dict['vulnerabilities'] = json.dumps([c.upper() for c in fields['cve'] if re.fullmatch(r'(?i)CVE-\d{4}-\d{4,}', c)])
    if fields.get('tags'):
        rule_dict['tags'] = [{'id': t} for t in _tag_ids(fields['tags'])]
    return rule_dict


def _tag_ids(values):
    """Tag ids from the panel: ids from the pickers, names when the tags were read from the rule."""
    from app.core.db_class.tag import Tag
    ids = [int(v) for v in values if str(v).isdigit()]
    names = [v for v in values if not str(v).isdigit()]
    if names:
        ids += [t.id for t in Tag.query.filter(Tag.name.in_(names))]
    return list(dict.fromkeys(ids))


def attach_relations(rule, fields, user):
    """Linked rules of the Fields panel, created once the rule exists (as the manual form does)."""
    if not fields or not fields.get('related'):
        return
    from app.features.rule_relation.rule_relation_core import add_relation
    for link in fields['related']:
        if link['id'] != rule.id:
            add_relation(rule.id, link['id'], link['kind'], user_id=user.id, source='manual')


def attach_attack(rule, fields, user):
    """ATT&CK techniques of the Fields panel, linked once the rule exists."""
    if not fields or not fields.get('attack'):
        return
    from app.features.attack.attack_core import add_technique_to_rule
    for tid in fields['attack']:
        if re.fullmatch(r'(?i)T\d{4}(\.\d{3})?', tid):
            try:
                add_technique_to_rule(rule.id, tid.upper(), user.id, source='manual')
            except Exception:
                pass


def _info(user):
    """Defaults parse_metadata falls back on (the user's licence and name), as the import does."""
    return {
        'license': getattr(user, 'license', None) or 'Unknown',
        'author': getattr(user, 'first_name', None) or 'Unknown',
        'repo_url': None,
    }


def new_rule_dict(e, user):
    """The rule dict Rulezet stores for this document rule: what the rule says (meta), with the
    Fields panel's values on top. The preview and the creation both use it."""
    return apply_fields(YaraRule().parse_metadata(e['content'], _info(user), _Validation(e['content'])), e.get('fields'))


def import_preview(e, user):
    """Every field Rulezet will store for a new rule, and where each value comes from:
    'panel' (Fields panel), 'rule' (the rule's meta / header), 'default' (Rulezet's default)."""
    from app.core.db_class.tag import Tag
    from app.core.utils.app_settings import get_setting
    fields = e.get('fields') or {}
    meta_values = {}
    for k, v in re.findall(r'^\s*(\w+)\s*=\s*"((?:[^"\\]|\\.)*)"', e['text'], re.M):
        meta_values.setdefault(k.lower(), v)
    meta = set(meta_values)
    d = new_rule_dict(e, user)

    def origin(field, *meta_keys):
        # a panel value that is just the rule's own meta value comes from the rule
        if field in fields and not any(str(fields[field]).strip() == meta_values.get(k, '').strip() for k in meta_keys):
            return 'panel'
        return 'rule' if any(k in meta for k in meta_keys) else 'default'

    vulns = RuleModel._parse_vulnerabilities(d.get('vulnerabilities')) or RuleModel._parse_vulnerabilities(d.get('cve_id'))
    tag_ids = [t['id'] for t in d.get('tags') or [] if isinstance(t, dict)]
    related = fields.get('related') or []
    related_titles = {r.id: r.title for r in RuleModel._active().filter(Rule.id.in_([x['id'] for x in related]))} if related else {}
    tag_names = [t.name for t in Tag.query.filter(Tag.id.in_(tag_ids))] if tag_ids else []
    defaults = list((get_setting('tags.defaults') or {}).get('auto_attach') or [])
    # the tags Rulezet attaches as "Imported" on creation, with the same detection
    from app.features.tags.imported_tags_core import extract_native_tags
    rule_tags = extract_native_tags('yara', e['content'])
    attack = [a.upper() for a in fields.get('attack') or [] if re.fullmatch(r'(?i)T\d{4}(\.\d{3})?', a)]
    rows = [
        {'id': 'title', 'label': 'Title', 'value': d.get('title'),
         'origin': 'panel' if fields.get('title') and fields['title'] != e['name'] else 'rule'},
        {'id': 'description', 'label': 'Description', 'value': d.get('description'), 'origin': origin('description', 'description', 'desc')},
        {'id': 'author', 'label': 'Author', 'value': d.get('author'), 'origin': origin('author', 'author')},
        {'id': 'license', 'label': 'License', 'value': d.get('license'), 'origin': origin('license', 'license')},
        {'id': 'version', 'label': 'Version', 'value': d.get('version'), 'origin': origin('version', 'version')},
        {'id': 'source', 'label': 'Source', 'value': d.get('source'), 'origin': origin('source', 'source')},
        {'id': 'original_uuid', 'label': 'Original UUID', 'value': d.get('original_uuid'), 'origin': origin('original_uuid', 'id', 'uuid')},
        {'id': 'cve', 'label': 'Vulnerabilities', 'value': vulns, 'origin': 'panel' if 'cve' in fields else ('rule' if vulns else 'default')},
        {'id': 'attack', 'label': 'ATT&CK techniques', 'value': attack, 'origin': 'panel' if attack else 'default'},
        {'id': 'tags', 'label': 'Chosen', 'group': 'Tags', 'value': tag_names, 'origin': 'panel' if tag_names else 'default'},
        {'id': 'related', 'label': 'Linked rules', 'origin': 'panel' if related else 'default',
         'value': [f"{related_titles[x['id']]} ({x['kind'].replace('_', ' ')})" for x in related if x['id'] in related_titles]},
        {'id': 'default_tags', 'label': 'Added by default', 'group': 'Tags', 'value': defaults, 'origin': 'default'},
        {'id': 'rule_tags', 'label': 'Imported from the rule', 'group': 'Tags', 'value': rule_tags, 'origin': 'rule'},
    ]
    return rows


def plan_yara(imports, rules, progress=None, user=None):
    """One entry per rule: status new | exists | update | proposal | error | blocked, with its
    dependencies. `user` decides between update and proposal for changed existing rules.
    progress(stage, done, total) is called as the checks go: 'existing' then 'syntax'."""
    tick = progress or (lambda *a: None)
    imports = [m for m in dict.fromkeys(imports or []) if re.fullmatch(r'\w+', str(m))]
    if not rules:
        return {'ok': False, 'rules': [], 'error': 'No rule in the document.'}
    if len(rules) > MAX_RULES:
        return {'ok': False, 'rules': [], 'error': f'Too many rules at once (max {MAX_RULES}).'}

    entries = []
    names = {}
    for r in rules:
        text = str(r.get('text') or '').strip()
        m = _HEADER.match(text)
        name = m.group(1) if m else str(r.get('name') or '')
        # a workspace sends the imports of each rule's own file
        own_imports = [m for m in (r.get('imports') or imports) if re.fullmatch(r'\w+', str(m))]
        used = [mod for mod in own_imports if re.search(rf'\b{mod}\s*\.', text)]
        content = ''.join(f'import "{mod}"\n' for mod in used) + ('\n' if used else '') + text
        entry = {'name': name, 'text': text, 'content': content, 'status': 'new', 'errors': [],
                 'depends_on': [], 'existing': None, 'path': r.get('path') or None,
                 'fields': clean_fields(r.get('fields'))}
        if not m:
            entry.update(status='error', errors=[{'message': 'Not a YARA rule'}])
        elif name in names:
            entry.update(status='error', errors=[{'message': f'Rule "{name}" is defined twice in the document'}])
        names.setdefault(name, entry)
        entries.append(entry)

    for i, e in enumerate(entries):
        if e['status'] == 'new':
            rule, reason = _existing(e['name'], e['content'], _meta_id(e['text']))
            if rule:
                e['existing'] = {**_rule_link(rule), 'reason': reason, 'owner_id': rule.user_id}
                if reason == 'same content' or _same_content(rule.to_string, e['content']) or _same_content(rule.to_string, e['text']):
                    e['status'] = 'exists'
                elif _can_edit(user, rule):
                    e['status'] = 'update'
                else:
                    open_proposal = RuleModel.find_open_duplicate(rule.id, e['content'])
                    e['status'] = 'proposal'
                    if open_proposal:
                        e['open_proposal'] = {'id': open_proposal.id, 'url': f'/rule/proposal_content_discuss?id={open_proposal.id}'}
        tick('existing', i + 1, len(entries))

    def deps_of(e):
        return [n for n in names if n != e['name'] and _condition_references(e['text'], n)]

    for i, e in enumerate(entries):
        tick('syntax', i, len(entries))
        if e['status'] not in PENDING:
            continue
        # compile with what it needs; unknown names are looked up in Rulezet
        found = {}                   # name -> ('document', entry) | ('rulezet', Rule)
        for n in deps_of(e):
            found[n] = ('document', names[n])
        extra_imports = set(imports)
        for _ in range(MAX_COMPILES):
            order, seen = [], set()

            def visit(n):
                if n in seen or n not in found:
                    return
                seen.add(n)
                kind, obj = found[n]
                text = obj['text'] if kind == 'document' else (obj.to_string or '')
                for sub in (deps_of(obj) if kind == 'document' else []):
                    found.setdefault(sub, ('document', names[sub]))
                    visit(sub)
                order.append(re.sub(r'^\s*import\s+"[^"]+"\s*$', '', text, flags=re.M))

            for n in list(found):
                visit(n)
            prefix = ''.join(f'import "{mod}"\n' for mod in sorted(extra_imports)) + ''.join(t + '\n' for t in order)
            try:
                yara.compile(source=prefix + e['text'], includes=False)
                break
            except yara.SyntaxError as err:
                message = str(err)
                missing = extract_undefined_identifier(message)
                if missing and missing in YaraRule.YARA_MODULES and missing not in extra_imports:
                    extra_imports.add(missing)
                    continue
                if missing and missing not in found:
                    if missing in names:
                        found[missing] = ('document', names[missing])
                        continue
                    rule = _rulezet_rule(missing)
                    if rule:
                        found[missing] = ('rulezet', rule)
                        continue
                    e['errors'].append({'message': f'Rule "{missing}" is not in the document nor in Rulezet'})
                    e['status'] = 'error'
                else:
                    located = _line_offset_error(message, prefix.count('\n'))
                    e['errors'].append(located)
                    # the error is in a rule it needs, not in this one
                    e['status'] = 'error' if 'line' in located or not order else 'blocked'
                break
            except yara.Error as err:
                e.update(status='error')
                e['errors'].append({'message': str(err)})
                break
        else:
            e.update(status='error', errors=[{'message': 'Too many dependencies to resolve'}])

        direct = set(deps_of(e)) | {n for n, (k, _) in found.items() if k == 'rulezet' and _condition_references(e['text'], n)}
        for n in sorted(direct):
            kind, obj = found.get(n, ('document', names.get(n)))
            if kind == 'rulezet':
                e['depends_on'].append({'name': n, 'where': 'rulezet', **_rule_link(obj)})
            else:
                e['depends_on'].append({'name': n, 'where': 'document'})

    tick('syntax', len(entries), len(entries))
    # a rule that needs a broken rule of the document cannot be created either
    changed = True
    while changed:
        changed = False
        for e in entries:
            if e['status'] not in PENDING + ('blocked',) or e.get('_propagated'):
                continue
            bad = [d['name'] for d in e['depends_on'] if d['where'] == 'document' and names[d['name']]['status'] in ('error', 'blocked')]
            if not bad and e['status'] == 'blocked':
                continue
            if bad:
                e.update(status='blocked', errors=[{'message': f'Needs {", ".join(bad)}, which has an error'}], _propagated=True)
                changed = True
    for e in entries:
        e.pop('_propagated', None)

    for e in entries:
        if e['status'] == 'new':          # what Rulezet will store, field by field (the Check shows it)
            try:
                e['preview'] = import_preview(e, user)
            except Exception:
                e['preview'] = None
    ok = all(e['status'] in PENDING + ('exists',) for e in entries)
    return {'ok': ok, 'rules': entries}


def import_yara(imports, rules, user, progress=None):
    """Checks again, then writes (creates, updates, proposes; dependencies first) and links each
    rule to the rules it needs. Writes nothing when one rule has an error."""
    plan = plan_yara(imports, rules, progress, user)
    if not plan['ok']:
        return plan
    return create_from_plan(plan, user)


def _update(e, rule, user):
    """The edit page's path: version bumped, history kept, dependency links refreshed."""
    from app.core.utils.utils import bump_version
    meta_description = re.search(r'\bdescription\s*=\s*"([^"]*)"', e['text'])
    rule_dict = {
        'format': rule.format, 'title': rule.title, 'license': rule.license,
        'description': meta_description.group(1) if meta_description else rule.description,
        'source': rule.source, 'version': bump_version(rule.version or '1.0'),
        'to_string': e['content'], 'author': rule.author, 'original_uuid': rule.original_uuid,
        'cve_id': rule.cve_id,
    }
    old_snapshot = RuleModel.rule_metadata_snapshot(rule)
    history_id = RuleModel.create_rule_history({
        'id': rule.id, 'title': rule.title, 'success': True, 'manual_submit': True,
        'message': 'Updated from the YARA editor', 'new_content': e['content'],
        'old_content': rule.to_string, 'old_snapshot': old_snapshot, 'analyzed_by_user_id': user.id,
    })
    ok, rule = RuleModel.edit_rule_core(rule_dict, rule.id)
    if not ok:
        return None
    history = RuleModel.get_history_rule_by_id(history_id) if history_id else None
    if history is not None:
        history.message = 'accepted'
        history.new_snapshot = RuleModel.rule_metadata_snapshot(rule)
        history.change_type = 'content'
        db.session.commit()
    if user.id != rule.user_id:
        RuleModel.add_contributor(user.id, rule.id)
    return rule


def _propose(e, rule, user):
    """An edit proposal to the owner, like "Propose an edit" on the rule page."""
    ok, proposal_id = RuleModel.propose_edit_core({
        'rule_id': rule.id, 'proposed_content': e['content'],
        'message': 'Proposed from the YARA editor', 'edit_type': 'content_update',
    }, user.id)
    if not ok:
        return None
    try:
        from app.core.db_class.rule_proposal import RuleEditProposal
        from app.features.notification.notification_core import notify_proposal_submitted
        notify_proposal_submitted(RuleEditProposal.query.get(proposal_id), rule)
    except Exception:
        pass
    return proposal_id


def create_from_plan(plan, user):
    """Writes a checked plan: new rules created, changed rules updated or proposed (dependencies
    first), then every written rule linked to the rules it needs."""
    from app.features.rule_relation.rule_relation_core import add_relation

    by_name = {e['name']: e for e in plan['rules']}
    written = {}                     # name -> Rule (created or updated)

    def write(e, stack=()):
        if e['status'] not in PENDING or e['name'] in written or e['name'] in stack:
            return
        for d in e['depends_on']:
            if d['where'] == 'document':
                write(by_name[d['name']], stack + (e['name'],))
        if e['status'] == 'new':
            rule_dict = new_rule_dict(e, user)
            rule, message = RuleModel.add_rule_core(rule_dict, user)
            if not rule:
                e.update(status='error', errors=[{'message': _refusal(message)}])
                return
            attach_attack(rule, e.get('fields'), user)
            attach_relations(rule, e.get('fields'), user)
            written[e['name']] = rule
            e.update(status='created', created=_rule_link(rule))
            return
        rule = Rule.query.get(e['existing']['id'])
        if not rule or rule.is_deleted:
            e.update(status='error', errors=[{'message': 'The rule to update is gone'}])
            return
        if e['status'] == 'update':
            if not _can_edit(user, rule):
                e.update(status='error', errors=[{'message': 'You may no longer edit this rule'}])
                return
            updated = _update(e, rule, user)
            if not updated:
                e.update(status='error', errors=[{'message': 'The rule could not be updated'}])
                return
            written[e['name']] = updated
            e.update(status='updated', created=_rule_link(updated))
        else:
            if e.get('open_proposal'):
                e.update(status='proposed', proposal=e['open_proposal'])
                return
            proposal_id = _propose(e, rule, user)
            if not proposal_id:
                e.update(status='error', errors=[{'message': 'The proposal could not be saved'}])
                return
            e.update(status='proposed', proposal={'id': proposal_id, 'url': f'/rule/proposal_content_discuss?id={proposal_id}'})

    for e in plan['rules']:
        write(e)

    for e in plan['rules']:
        rule = written.get(e['name'])
        if not rule:
            continue
        for d in e['depends_on']:
            if d['where'] == 'rulezet':
                target = d['id']
            else:
                dep = by_name[d['name']]
                target = written[d['name']].id if d['name'] in written else (dep['existing'] or {}).get('id')
            if target:
                add_relation(rule.id, target, 'yara_condition_ref', user_id=user.id, source='auto')

    plan['ok'] = all(e['status'] in ('created', 'updated', 'proposed', 'exists') for e in plan['rules'])
    plan['created'] = sum(1 for e in plan['rules'] if e['status'] == 'created')
    plan['updated'] = sum(1 for e in plan['rules'] if e['status'] == 'updated')
    plan['proposed'] = sum(1 for e in plan['rules'] if e['status'] == 'proposed')
    params = [f"created={e['created']['id']}" for e in plan['rules'] if e['status'] == 'created']
    params += [f"updated={e['created']['id']}" for e in plan['rules'] if e['status'] == 'updated']
    params += [f"proposed={e['existing']['id']}-{e['proposal']['id']}" for e in plan['rules'] if e['status'] == 'proposed']
    params += [f"reused={e['existing']['id']}" for e in plan['rules'] if e['status'] == 'exists']
    plan['result_url'] = '/editor/import-result?' + '&'.join(params)
    return plan


def import_result(created_ids, reused_ids, updated_ids=(), proposed=()):
    """What the result page shows: each rule written or reused, with the links it got.
    proposed: [(rule_id, proposal_id)]."""
    from app.core.db_class.rule_relation import RuleRelation

    created_ids, updated_ids = list(created_ids), list(updated_ids)
    proposal_of = dict(proposed)
    ids = list(dict.fromkeys(created_ids + list(updated_ids) + list(proposal_of) + list(reused_ids)))[:MAX_RULES]
    rules = {r.id: r for r in RuleModel._active().filter(Rule.id.in_(ids))} if ids else {}
    relations = RuleRelation.query.filter(
        db.or_(RuleRelation.source_rule_id.in_(ids), RuleRelation.target_rule_id.in_(ids))).all() if ids else []
    targets = {r.id: r for r in RuleModel._active().filter(
        Rule.id.in_({x.target_rule_id for x in relations} | {x.source_rule_id for x in relations}))} if relations else {}
    written = set(created_ids) | set(updated_ids)

    def card(rule_id, status):
        rule = rules.get(rule_id)
        if not rule:
            return None
        needs = [targets[x.target_rule_id] for x in relations
                 if x.source_rule_id == rule_id and x.target_rule_id in targets]
        needed_by = [targets[x.source_rule_id] for x in relations
                     if x.target_rule_id == rule_id and x.source_rule_id in targets and x.source_rule_id in written]
        proposal_id = proposal_of.get(rule_id)
        return {'rule': rule, 'status': status, 'needs': needs, 'needed_by': needed_by,
                'proposal_url': f'/rule/proposal_content_discuss?id={proposal_id}' if proposal_id else None}

    cards = lambda ids_, status: [c for c in (card(i, status) for i in ids_) if c]   # noqa: E731
    created = cards(created_ids, 'created')
    updated = cards(updated_ids, 'updated')
    proposals = cards(list(proposal_of), 'proposed')
    reused = cards([i for i in reused_ids if i not in written and i not in proposal_of], 'reused')
    links = sum(len(c['needs']) for c in created + updated)
    return {'created': created, 'updated': updated, 'proposals': proposals, 'reused': reused, 'links': links}
