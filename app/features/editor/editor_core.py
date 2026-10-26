"""Rule editor (app/modules/rulezet-editor) backed by this Rulezet: its validation and its
rules, called as Python functions. Never an HTTP call to rulezet.org.
See app/modules/rulezet-editor/docs/rulezet/ for what each editor feature uses here."""
import re

import yara
from rulezet_editor import FunctionBackend

from app import db
from app.core.db_class.rule import Rule
from app.features.rule import rule_core as RuleModel
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


backend = FunctionBackend(name='Rulezet', validate=validate, search_rules=search_rules, get_rule=get_rule)


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
        return TestService(remote, remote)
    extra = [d for d in os.environ.get('RULE_TESTS_SAMPLES', '').split(os.pathsep) if d.strip()]
    return TestService(FolderSampleStore(SAMPLES, *extra), Sandbox(mode=mode))


tests = _test_service()


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
                 'depends_on': [], 'existing': None, 'path': r.get('path') or None}
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
                yara.compile(source=prefix + e['text'])
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
    info = {
        'license': getattr(user, 'license', None) or 'Unknown',
        'author': getattr(user, 'first_name', None) or 'Unknown',
        'repo_url': None,
    }
    written = {}                     # name -> Rule (created or updated)

    def write(e, stack=()):
        if e['status'] not in PENDING or e['name'] in written or e['name'] in stack:
            return
        for d in e['depends_on']:
            if d['where'] == 'document':
                write(by_name[d['name']], stack + (e['name'],))
        if e['status'] == 'new':
            rule_dict = YaraRule().parse_metadata(e['content'], info, _Validation(e['content']))
            rule, message = RuleModel.add_rule_core(rule_dict, user)
            if not rule:
                e.update(status='error', errors=[{'message': _refusal(message)}])
                return
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
