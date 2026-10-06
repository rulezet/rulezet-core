"""Rule factories and the payloads the rule forms / API expect."""
import datetime
import itertools
import uuid

from app import db
from app.core.db_class.db import Rule

_counter = itertools.count(1)


def yara_rule(name):
    """Valid YARA content with a unique rule name."""
    return f'rule {name} {{\n    strings:\n        $a = "{name}"\n    condition:\n        $a\n}}'


def make_rule(owner, **overrides):
    """An active YARA rule owned by `owner`, unique title/content per call."""
    n = next(_counter)
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    fields = dict(
        format="yara",
        title=f"Test rule {n}",
        license="MIT",
        description=f"Description of test rule {n}",
        uuid=str(uuid.uuid4()),
        source="tests",
        author="Tester",
        version="1",
        user_id=owner.id,
        creation_date=now,
        last_modif=now,
        vote_up=0,
        vote_down=0,
        to_string=yara_rule(f"test_rule_{n}"),
    )
    fields.update(overrides)
    rule = Rule(**fields)
    db.session.add(rule)
    db.session.commit()
    return rule


def new_rule_form(**overrides):
    """What the "create rule" form posts, for a new valid YARA rule."""
    n = next(_counter)
    form = dict(
        format="yara",
        title=f"Created rule {n}",
        license="MIT",
        version="1",
        description="Created through the form",
        source="tests",
        to_string=yara_rule(f"created_rule_{n}"),
    )
    form.update(overrides)
    return form


def edit_form(rule, **changes):
    """What the "edit rule" form posts for `rule`, with `changes` applied."""
    form = dict(
        format=rule.format,
        title=rule.title,
        license=rule.license,
        version=rule.version,
        description=rule.description or "",
        source=rule.source or "",
        to_string=rule.to_string,
    )
    form.update(changes)
    return form

