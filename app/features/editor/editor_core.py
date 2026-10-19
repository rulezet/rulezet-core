"""Rule editor (app/modules/rulezet-editor) backed by this Rulezet: its validation and its
rules, called as Python functions. Never an HTTP call to rulezet.org.
See app/modules/rulezet-editor/docs/rulezet/ for what each editor feature uses here."""
from rulezet_editor import FunctionBackend

from app.core.db_class.rule import Rule
from app.features.rule import rule_core as RuleModel


def validate(fmt, content):
    """The check a rule goes through on creation; YARA rules are compiled together with the
    Rulezet rules they reference. None for an unknown format (the editor shows nothing)."""
    return RuleModel.validate_rule_syntax(fmt, content, resolve_dependencies=True)


def _rule_item(rule):
    return {
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
