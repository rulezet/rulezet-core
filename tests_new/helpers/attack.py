"""ATT&CK factories — a handful of techniques instead of the real MITRE CTI."""
import datetime
import uuid

from app import db
from app.core.db_class.db import AttackTechnique, RuleAttackAssociation

_NAMES = {
    "T1059": "Command and Scripting Interpreter",
    "T1059.001": "PowerShell",
    "T1105": "Ingress Tool Transfer",
    "T1068": "Exploitation for Privilege Escalation",
    "T1190": "Exploit Public-Facing Application",
}

_TACTICS = {
    "T1059": ["execution"],
    "T1059.001": ["execution"],
    "T1105": ["command-and-control"],
    "T1068": ["privilege-escalation"],
    "T1190": ["initial-access"],
}


def make_technique(technique_id="T1059", *, name=None, tactics=None, deprecated=False):
    """An ATT&CK technique as the CTI import stores it (sub-technique when
    the id has a dot)."""
    is_sub = "." in technique_id
    technique = AttackTechnique(
        technique_id=technique_id,
        name=name or _NAMES.get(technique_id, f"Technique {technique_id}"),
        tactic_keys=tactics if tactics is not None else _TACTICS.get(technique_id, ["execution"]),
        description=f"Description of {technique_id}",
        url=f"https://attack.mitre.org/techniques/{technique_id.replace('.', '/')}/",
        is_subtechnique=is_sub,
        parent_technique_id=technique_id.split(".")[0] if is_sub else None,
        deprecated=deprecated,
        updated_at=datetime.datetime.now(tz=datetime.timezone.utc),
    )
    db.session.add(technique)
    db.session.commit()
    return technique


def link_technique(rule, technique, user=None, source="manual"):
    """`technique` mapped on `rule` (by `user`, or auto-parsed when None)."""
    assoc = RuleAttackAssociation(
        uuid=str(uuid.uuid4()),
        rule_id=rule.id,
        technique_id=technique.technique_id,
        user_id=user.id if user else None,
        source=source,
        added_at=datetime.datetime.now(tz=datetime.timezone.utc),
    )
    db.session.add(assoc)
    db.session.commit()
    return assoc


def trash(rule, by):
    """Soft-delete `rule` the way the trash does."""
    rule.is_deleted = True
    rule.deleted_by_id = by.id
    rule.deleted_at = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.commit()
    return rule
