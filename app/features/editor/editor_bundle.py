"""Bundles from the editor's workspace (folders and files of YARA rules), and back.

Workspace tree (the editor's explorer):
    {type: 'folder', name, children: [...]}
    {type: 'file', name: 'apt.yar', rules: ['rule_a', 'rule_b']}      YARA file: names of its rules
    {type: 'file', name: 'README.md', content: '...'}                 any other file: plain text

Bundle structure (BundleNode, see bundle_core.validate_structure / save_workspace):
    a YARA file with one rule      -> a rule node
    a YARA file with several rules -> a folder named after the file, one rule node per rule
    any other file                 -> a custom file node (content kept)
"""
from app.core.db_class.bundle import Bundle, BundleNode
from app.features.bundle import bundle_core as BundleModel
from app.features.bundle.bundle_history_core import track_bundle_change

from .editor_core import _can_edit

YARA_EXTENSIONS = ('.yar', '.yara')
MAX_TREE_NODES = 5000


def is_yara_file(name):
    return str(name or '').lower().endswith(YARA_EXTENSIONS)


def can_edit_bundle(user, bundle):
    """Same rule as /bundle/save_workspace: the owner or an admin."""
    return bool(user) and bundle is not None and (user.id == bundle.user_id or user.is_admin())


def _stem(name):
    return name.rsplit('.', 1)[0] if '.' in name else name


def to_bundle_structure(tree, rule_ids):
    """Workspace tree -> bundle structure. rule_ids: rule name -> Rule id (written or reused)."""
    def convert(node):
        if node.get('type') == 'folder':
            return [{'type': 'folder', 'name': node.get('name') or 'folder',
                     'children': [c for child in node.get('children') or [] for c in convert(child)]}]
        name = node.get('name') or 'file'
        if not is_yara_file(name):
            return [{'type': 'file', 'name': name, 'content': node.get('content') or ''}]
        ids = [rule_ids[r] for r in node.get('rules') or [] if r in rule_ids]
        files = [{'type': 'file', 'name': r, 'rule_id': i} for r, i in zip(node.get('rules') or [], ids)]
        if len(files) == 1:
            return files
        return [{'type': 'folder', 'name': _stem(name), 'children': files}] if files else []
    return [c for node in tree or [] for c in convert(node)]


def check_bundle_request(spec, user):
    """Error message, or None. spec: {mode: 'create' | 'update', bundle_id, name, description, public}."""
    if not spec:
        return None
    if spec.get('mode') == 'update':
        bundle = Bundle.query.get(spec.get('bundle_id') or 0)
        if not bundle:
            return 'Bundle not found.'
        if not can_edit_bundle(user, bundle):
            return 'You may not edit this bundle: save it as a new bundle instead.'
        return None
    name = str(spec.get('name') or '').strip()
    if not name:
        return 'The bundle needs a name.'
    if len(name) > 255:
        return 'Bundle name too long.'
    if BundleModel.bundle_name_taken(name, user.id):
        return f'You already have a bundle named "{name}".'
    return None


def write_bundle(spec, tree, rule_ids, user):
    """Creates or updates the bundle with the workspace's structure. (bundle, error)."""
    error = check_bundle_request(spec, user)
    if error:
        return None, error
    structure = to_bundle_structure(tree, rule_ids)
    error = BundleModel.validate_structure(structure)
    if error:
        return None, error
    if spec.get('mode') == 'update':
        bundle = Bundle.query.get(spec['bundle_id'])
    else:
        bundle = BundleModel.create_bundle({
            'name': spec['name'].strip(),
            'description': spec.get('description') or '',
            'public': bool(spec.get('public', True)),
        }, user)
        if not bundle:
            return None, 'The bundle could not be created.'
    with track_bundle_change(bundle.id, 'structure', user=user):
        if not BundleModel.update_bundle_from_structure(bundle.id, structure):
            return bundle, 'The rules could not be added to the bundle.'
        if not BundleModel.save_workspace(bundle.id, structure):
            return bundle, 'The bundle structure could not be saved.'
    return bundle, None


def workspace_from_bundle(bundle, user):
    """Bundle -> workspace tree for the editor. Rule files carry their content and whether the
    user may edit the rule (otherwise the editor locks it)."""
    count = [0]

    def convert(node):
        count[0] += 1
        if count[0] > MAX_TREE_NODES:
            return None
        if node.node_type == 'folder':
            return {'type': 'folder', 'name': node.name,
                    'children': [c for c in (convert(ch) for ch in node.children) if c]}
        if node.rule_id:
            rule = node.rule
            if not rule or rule.is_deleted:
                return None
            ext = '.yar' if (rule.format or '').lower() == 'yara' else f'.{(rule.format or "txt").lower()}'
            return {'type': 'file', 'name': f'{rule.title}{ext}', 'content': rule.to_string or '',
                    'rule': {'id': rule.id, 'name': rule.title, 'can_edit': _can_edit(user, rule),
                             'url': f'/rule/detail_rule/{rule.id}', 'format': rule.format}}
        return {'type': 'file', 'name': node.name, 'content': node.custom_content or ''}

    roots = BundleNode.query.filter_by(bundle_id=bundle.id, parent_id=None).order_by(BundleNode.id).all()
    tree = [c for c in (convert(n) for n in roots) if c]
    return {
        'bundle': {'id': bundle.id, 'uuid': bundle.uuid, 'name': bundle.name, 'description': bundle.description or '',
                   'public': bool(bundle.access), 'can_edit': can_edit_bundle(user, bundle),
                   'url': f'/bundle/detail/{bundle.id}'},
        'tree': tree,
    }
