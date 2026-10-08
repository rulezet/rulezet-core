import uuid as _uuid
import datetime
from ... import db
from ...core.db_class.db import Workspace, WorkspaceRule, WorkspaceBundle, Bundle, Rule


def get_user_workspaces(user_id: int) -> list:
    return Workspace.query.filter_by(user_id=user_id).order_by(Workspace.name).all()


def get_all_workspaces() -> list:
    """Every workspace on the instance, regardless of owner — admin-only view."""
    return Workspace.query.order_by(Workspace.name).all()


def get_workspace_by_uuid(uuid_str: str):
    return Workspace.query.filter_by(uuid=uuid_str).first()


def create_workspace(user_id: int, name: str, description: str = None,
                     icon: str = 'fa-folder', color: str = '#0d6efd') -> Workspace:
    ws = Workspace(
        uuid=str(_uuid.uuid4()),
        name=name.strip(),
        description=description,
        icon=icon,
        color=color,
        user_id=user_id,
    )
    db.session.add(ws)
    db.session.commit()
    return ws


def update_workspace(ws: Workspace, name: str = None, description: str = None,
                     icon: str = None, color: str = None) -> Workspace:
    if name is not None:
        ws.name = name.strip()
    if description is not None:
        ws.description = description
    if icon is not None:
        ws.icon = icon
    if color is not None:
        ws.color = color
    ws.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.commit()
    return ws


def delete_workspace(ws: Workspace):
    db.session.delete(ws)
    db.session.commit()


def add_rule_to_workspace(ws: Workspace, rule_id: int) -> bool:
    if WorkspaceRule.query.filter_by(workspace_id=ws.id, rule_id=rule_id).first():
        return False
    db.session.add(WorkspaceRule(workspace_id=ws.id, rule_id=rule_id))
    ws.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.commit()
    return True


def bulk_add_rules_to_workspace(ws: Workspace, rule_ids: list) -> int:
    added = 0
    for rid in rule_ids:
        if not WorkspaceRule.query.filter_by(workspace_id=ws.id, rule_id=rid).first():
            db.session.add(WorkspaceRule(workspace_id=ws.id, rule_id=rid))
            added += 1
    if added:
        ws.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
        db.session.commit()
    return added


def remove_rule_from_workspace(ws: Workspace, rule_id: int) -> bool:
    wr = WorkspaceRule.query.filter_by(workspace_id=ws.id, rule_id=rule_id).first()
    if not wr:
        return False
    db.session.delete(wr)
    ws.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.commit()
    return True


def get_workspace_rule_ids(ws: Workspace) -> list:
    """Active (non-deleted) rule ids currently in a workspace — feeds the
    "Export as Bundle" action."""
    return [
        rid for (rid,) in db.session.query(WorkspaceRule.rule_id)
        .join(Rule, Rule.id == WorkspaceRule.rule_id)
        .filter(WorkspaceRule.workspace_id == ws.id, Rule.is_deleted == False)
        .all()
    ]


# ── Bundles collected in a workspace ────────────────────────────────────────

def add_bundle_to_workspace(ws: Workspace, bundle_id: int, commit: bool = True) -> bool:
    if WorkspaceBundle.query.filter_by(workspace_id=ws.id, bundle_id=bundle_id).first():
        return False
    db.session.add(WorkspaceBundle(workspace_id=ws.id, bundle_id=bundle_id))
    ws.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    if commit:
        db.session.commit()
    return True


def remove_bundle_from_workspace(ws: Workspace, bundle_id: int) -> bool:
    """Drop the workspace ↔ bundle link. Also clears the "exported from this
    workspace" provenance so the bundle doesn't reappear. The bundle itself
    is never touched."""
    wb = WorkspaceBundle.query.filter_by(workspace_id=ws.id, bundle_id=bundle_id).first()
    bundle = Bundle.query.get(bundle_id)
    exported_here = bool(bundle and bundle.source_workspace_id == ws.id)
    if not wb and not exported_here:
        return False
    if wb:
        db.session.delete(wb)
    if exported_here:
        bundle.source_workspace_id = None
    ws.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.commit()
    return True


def get_workspace_bundle_links(ws: Workspace) -> list:
    """(WorkspaceBundle, Bundle) pairs, newest first."""
    return (
        db.session.query(WorkspaceBundle, Bundle)
        .join(Bundle, Bundle.id == WorkspaceBundle.bundle_id)
        .filter(WorkspaceBundle.workspace_id == ws.id)
        .order_by(WorkspaceBundle.added_at.desc())
        .all()
    )
