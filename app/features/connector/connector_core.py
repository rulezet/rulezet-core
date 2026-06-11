"""
connector_core.py — Business logic for the Connector feature.

All DB interactions stay here. Blueprints and API namespaces call these
functions and never touch the session directly.
"""

import datetime
import uuid as uuid_mod
import logging

import requests as http_requests
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

from app import db
from app.core.db_class.db import (
    Bundle, BundleRuleAssociation, Connector, Rule, User,
    RuleTagAssociation, Tag, ActivityLog, RuleUpdateHistory,
)
from app.core.utils.activity_log import log_activity
from app.features.jobs.jobs_core import create_job


# ─── Shadow user ──────────────────────────────────────────────────────────────

def _get_or_create_shadow_user(connector: Connector) -> User:
    """Return (and lazily create) the ghost user that owns imported content."""
    if connector.shadow_user_id:
        user = User.query.get(connector.shadow_user_id)
        if user:
            return user

    shadow_email = f"shadow_{connector.uuid[:8]}@connector.local"
    existing = User.query.filter_by(email=shadow_email).first()
    if existing:
        connector.shadow_user_id = existing.id
        db.session.commit()
        return existing

    shadow = User(
        first_name=connector.name,
        last_name=f"[{connector.connector_type}]",
        email=shadow_email,
        username=f"connector_{connector.uuid[:8]}",
        is_verified=False,
        admin=False,
    )
    shadow.password = uuid_mod.uuid4().hex   # random password — cannot login
    try:
        db.session.add(shadow)
        db.session.flush()
    except IntegrityError:
        # Another concurrent call already created this shadow user
        db.session.rollback()
        existing = User.query.filter_by(email=shadow_email).first()
        if existing:
            connector.shadow_user_id = existing.id
            db.session.commit()
            return existing
        raise

    connector.shadow_user_id = shadow.id
    db.session.commit()
    return shadow


# ─── CRUD ─────────────────────────────────────────────────────────────────────

def get_connectors(owner_id: int) -> list:
    """Return user's own connectors + all system connectors."""
    from sqlalchemy import or_
    return (Connector.query
            .filter(or_(Connector.owner_id == owner_id, Connector.is_system == True))
            .order_by(Connector.is_system.desc(), Connector.created_at.desc())
            .all())


def get_connector_by_uuid(connector_uuid: str, owner_id: int = None) -> Connector | None:
    q = Connector.query.filter_by(uuid=connector_uuid)
    if owner_id is not None:
        q = q.filter_by(owner_id=owner_id)
    return q.first()


def create_connector(owner_id: int, name: str, instance_url: str,
                     connector_type: str = 'rulezet',
                     api_key_outbound: str = None,
                     description: str = None,
                     icon: str = None,
                     sync_rules: bool = True,
                     sync_bundles: bool = False,
                     owner_mode: str = 'shadow') -> Connector | None:
    try:
        url = instance_url.rstrip('/')
        connector = Connector(
            uuid=str(uuid_mod.uuid4()),
            name=name.strip(),
            description=description,
            icon=icon,
            connector_type=connector_type,
            instance_url=url,
            api_key_outbound=api_key_outbound,
            owner_id=owner_id,
            sync_rules=sync_rules,
            sync_bundles=sync_bundles,
            owner_mode=owner_mode,
        )
        db.session.add(connector)
        db.session.flush()
        _get_or_create_shadow_user(connector)   # eagerly create shadow user
        db.session.commit()

        log_activity('connector.create',
                     f"Created connector '{name}' → {url}",
                     target_type='connector', target_id=connector.id,
                     target_uuid=connector.uuid)
        return connector
    except Exception as e:
        db.session.rollback()
        print(f"[connector_core] create_connector error: {e}")
        return None


def update_connector(connector: Connector, data: dict) -> bool:
    if connector.is_system:
        return False
    try:
        allowed = ('name', 'description', 'icon', 'instance_url', 'api_key_outbound',
                   'sync_rules', 'sync_bundles', 'is_active', 'owner_mode')
        for key in allowed:
            if key in data:
                val = data[key]
                if key == 'instance_url' and val:
                    val = val.rstrip('/')
                setattr(connector, key, val)
        connector.updated_at = datetime.datetime.now(datetime.timezone.utc)
        db.session.commit()
        log_activity('connector.update', f"Updated connector '{connector.name}'",
                     target_type='connector', target_id=connector.id,
                     target_uuid=connector.uuid)
        return True
    except Exception as e:
        db.session.rollback()
        print(f"[connector_core] update_connector error: {e}")
        return False


def delete_connector(connector: Connector) -> bool:
    if connector.is_system:
        return False
    try:
        name = connector.name
        cid  = connector.id
        cuuid = connector.uuid
        # Nullify FK on rules/bundles so we don't lose data
        Rule.query.filter_by(connector_id=cid).update({'connector_id': None}, synchronize_session=False)
        Bundle.query.filter_by(connector_id=cid).update({'connector_id': None}, synchronize_session=False)
        db.session.delete(connector)
        db.session.commit()
        log_activity('connector.delete', f"Deleted connector '{name}'",
                     extra={'connector_uuid': cuuid})
        return True
    except Exception as e:
        db.session.rollback()
        print(f"[connector_core] delete_connector error: {e}")
        return False


# ─── Connection test ──────────────────────────────────────────────────────────

def test_connector(connector: Connector) -> tuple[bool, str, dict]:
    """
    Ping the remote /api/sync/manifest then /api/sync/stats.
    Returns (success: bool, message: str, stats: dict).
    stats contains 'rules' and 'bundles' counts from the remote (or {}).
    """
    base    = connector.instance_url
    headers = {}
    if connector.api_key_outbound:
        headers['X-API-KEY'] = connector.api_key_outbound
    try:
        resp = http_requests.get(f"{base}/api/sync/manifest", headers=headers, timeout=8)
        if resp.status_code == 404:
            msg = ("Sync API not found (HTTP 404). The remote instance may be running an older version "
                   "of Rulezet that does not support federation sync.")
            connector.last_error = msg
            db.session.commit()
            return False, msg, {}
        if resp.status_code != 200:
            msg = f"Remote returned HTTP {resp.status_code}."
            connector.last_error = msg
            db.session.commit()
            return False, msg, {}

        remote_name = resp.json().get('instance', {}).get('name', 'unknown')

        # Fetch public stats (best-effort — non-fatal if absent)
        stats: dict = {}
        try:
            sr = http_requests.get(f"{base}/api/sync/stats", headers=headers, timeout=5)
            if sr.status_code == 200:
                sd = sr.json()
                stats = {'rules': sd.get('rules'), 'bundles': sd.get('bundles')}
        except Exception:
            pass

        connector.is_verified = True
        connector.last_error  = None
        if stats.get('rules') is not None:
            connector.remote_rules_count   = stats['rules']
        if stats.get('bundles') is not None:
            connector.remote_bundles_count = stats['bundles']
        db.session.commit()

        stats_str = ''
        if stats.get('rules') is not None:
            stats_str = f" — {stats['rules']:,} rules, {stats['bundles']:,} bundles"

        log_activity('connector.test_ok',
                     f"Connection test OK for '{connector.name}' → {remote_name}{stats_str}",
                     target_type='connector', target_id=connector.id,
                     target_uuid=connector.uuid)
        return True, f"Connected to \"{remote_name}\"{stats_str}.", stats

    except Exception as e:
        msg = f"Connection error: {e}"
        connector.last_error = msg
        db.session.commit()
        return False, msg, {}


# ─── Pull (trigger background job) ───────────────────────────────────────────

def get_connector_history(connector: Connector) -> list:
    """Return the last 30 activity log entries for this connector."""
    entries = (ActivityLog.query
               .filter(
                   ActivityLog.target_type == 'connector',
                   ActivityLog.target_id == connector.id,
               )
               .order_by(ActivityLog.created_at.desc())
               .limit(30)
               .all())
    return [
        {
            'action':      e.action,
            'description': e.description,
            'timestamp':   e.created_at.strftime('%Y-%m-%d %H:%M:%S') if e.created_at else None,
            'extra':       e.extra or {},
        }
        for e in entries
    ]


def seed_official_connector() -> None:
    """Create the read-only official Rulezet connector if it doesn't exist yet."""
    try:
        if Connector.query.filter_by(is_system=True).first():
            return
        admin = User.query.filter_by(admin=True).first()
        if not admin:
            return
        c = Connector(
            uuid=str(uuid_mod.uuid4()),
            name='Rulezet Official',
            description='The official Rulezet community — rulezet.org.',
            icon='fa-solid fa-shield-halved',
            connector_type='rulezet',
            instance_url='https://rulezet.org',
            owner_id=admin.id,
            sync_rules=True,
            sync_bundles=True,
            is_system=True,
            owner_mode='shadow',
        )
        db.session.add(c)
        db.session.commit()
    except Exception:
        db.session.rollback()


def trigger_pull(connector: Connector, triggered_by: int, mode: str = 'soft') -> object | None:
    """Enqueue a connector_pull background job and return the job object.

    mode:
        'soft' — add only new rules/bundles, skip any that already exist locally
        'hard' — add new + overwrite existing if the remote version is newer
    """
    if not connector.is_active:
        return None
    if mode not in ('soft', 'hard'):
        mode = 'soft'
    label = f"Pull [{mode}] from '{connector.name}'"
    job = create_job(
        job_type='connector_pull',
        payload={'connector_id': connector.id, 'mode': mode},
        label=label,
        created_by=triggered_by,
    )
    log_activity('connector.pull_triggered',
                 f"Pull queued for connector '{connector.name}' (mode: {mode})",
                 target_type='connector', target_id=connector.id,
                 target_uuid=connector.uuid,
                 extra={'job_uuid': job.uuid if job else None, 'mode': mode})
    return job


# ─── Sync helpers (called from job handler) ───────────────────────────────────

def _upsert_rule(connector: Connector, shadow_user_id: int, remote: dict,
                 mode: str = 'soft', triggered_by_id: int = None) -> str:
    """
    Matching is by UUID only (remote canonical uuid vs local remote_rule_uuid
    or uuid) — content is never compared.

    soft: local match (even in trash) → skip. No match → create.

    hard: local match → if the remote version differs, import it over the
          local rule in place. A content (to_string) change is archived first
          in RuleUpdateHistory (old_content = local, new_content = remote);
          metadata-only changes (title, description, …) are applied without
          a history entry. A match found in the trash is restored. Identical
          active rule → skip.
          No match → create + import remote history.

    Returns: 'created' | 'updated' | 'skipped' | 'invalid'
    """
    remote_uuid = remote.get('uuid')
    if not remote_uuid:
        return 'invalid'

    owner_id = triggered_by_id if (mode == 'hard' and triggered_by_id) else shadow_user_id
    now      = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    # ── Find local match by uuid only ─────────────────────────────────────────
    # Rule.uuid is also checked so a rule that originated here and comes back
    # from a remote instance is recognised instead of duplicated. Trashed rules
    # are matched too (active ones first) so a hard pull can restore them and
    # a soft pull does not recreate a rule the local admin deleted.
    local_match = Rule.query.filter(
        or_(Rule.remote_rule_uuid == remote_uuid, Rule.uuid == remote_uuid),
    ).order_by(Rule.is_deleted.asc()).first()

    if local_match:
        # ── Soft mode: existence (even in trash) → skip ───────────────────────
        if mode == 'soft':
            return 'skipped'

        # ── Hard mode: import the remote version over the local rule ─────────
        restored = False
        if local_match.is_deleted:
            local_match.is_deleted        = False
            local_match.deleted_at        = None
            local_match.deleted_by_id     = None
            local_match.delete_batch_uuid = None
            restored = True

        new_content     = remote.get('to_string', '')
        content_changed = (local_match.to_string or '') != new_content

        if content_changed:
            # Archive the version being overwritten before touching it
            db.session.add(RuleUpdateHistory(
                rule_id=local_match.id,
                rule_title=local_match.title,
                success=True,
                message=f"Updated by pull from '{connector.name}' ({connector.instance_url})",
                old_content=local_match.to_string,
                new_content=new_content,
                analyzed_by_user_id=owner_id,
                analyzed_at=now,
                manuel_submit=False,
            ))
            local_match.to_string = new_content

        meta_changed = False
        for field in ('format', 'title', 'description', 'author', 'version', 'license', 'source'):
            value = remote.get(field)
            if value is None:
                continue
            if field == 'version':
                value = str(value)
            if getattr(local_match, field) != value:
                setattr(local_match, field, value)
                meta_changed = True

        if not content_changed and not meta_changed and not restored:
            return 'skipped'

        local_match.connector_id      = connector.id
        local_match.sync_instance_url = connector.instance_url
        local_match.last_modif        = now
        db.session.flush()

        _sync_tags(local_match, remote.get('tags', []), owner_id)
        _import_rule_history(local_match, remote.get('update_history', []), owner_id)
        return 'updated'

    # ── No match → create the rule from remote data ───────────────────────────
    rule = Rule(
        uuid=str(uuid_mod.uuid4()),
        remote_rule_uuid=remote_uuid,
        connector_id=connector.id,
        user_id=owner_id,
        format=remote.get('format', 'unknown'),
        title=remote.get('title', ''),
        description=remote.get('description'),
        to_string=remote.get('to_string', ''),
        author=remote.get('author') or connector.name,
        source=remote.get('source'),
        sync_instance_url=connector.instance_url,
        version=remote.get('version'),
        license=remote.get('license'),
        vote_up=0,
        vote_down=0,
        creation_date=now,
        last_modif=now,
        is_deleted=False,
    )
    db.session.add(rule)
    db.session.flush()
    _sync_tags(rule, remote.get('tags', []), owner_id)
    _import_rule_history(rule, remote.get('update_history', []), owner_id)
    return 'created'


def _import_rule_history(rule: Rule, history: list, fallback_user_id: int) -> None:
    """Attach RuleUpdateHistory entries to a rule, deduplicating by analyzed_at
    (both within the batch and against entries already stored for the rule)."""
    if not history:
        return
    seen = {
        h.analyzed_at.isoformat()
        for h in rule.rule_update_history.all()
        if h.analyzed_at
    }
    for h in history:
        try:
            if h.get('analyzed_at'):
                raw = datetime.datetime.fromisoformat(
                    h['analyzed_at'].replace('Z', '+00:00')
                ).replace(tzinfo=None)
            else:
                raw = datetime.datetime.utcnow()
            key = raw.isoformat()
            if key in seen:
                continue
            seen.add(key)
            db.session.add(RuleUpdateHistory(
                rule_id=rule.id,
                rule_title=rule.title,
                success=h.get('success', True),
                message=h.get('message'),
                old_content=h.get('old_content'),
                new_content=h.get('new_content'),
                analyzed_by_user_id=fallback_user_id,
                analyzed_at=raw,
                manuel_submit=h.get('manuel_submit', False),
            ))
        except Exception as exc:
            logger.warning("_import_rule_history: skipped entry for rule %s: %s", rule.id, exc)


def _sync_tags(rule: Rule, tag_names: list, user_id: int) -> None:
    """Attach tags that already exist locally; silently skip unknown ones."""
    for name in tag_names:
        tag = Tag.query.filter(Tag.name.ilike(name)).first()
        if not tag:
            continue
        already = RuleTagAssociation.query.filter_by(rule_id=rule.id, tag_id=tag.id).first()
        if not already:
            db.session.add(RuleTagAssociation(
                uuid=str(uuid_mod.uuid4()),
                rule_id=rule.id,
                tag_id=tag.id,
                user_id=user_id,
                added_at=datetime.datetime.now(datetime.timezone.utc),
            ))


def _sync_bundle_rules(bundle: Bundle, rule_uuids: list) -> int:
    """Attach local rules (matched by uuid) to the bundle.
    Additive only — never removes rules a local user added. Returns the
    number of new associations created."""
    added = 0
    for r_uuid in rule_uuids or []:
        rule = Rule.query.filter(
            Rule.is_deleted == False,
            or_(Rule.remote_rule_uuid == r_uuid, Rule.uuid == r_uuid),
        ).first()
        if rule is None:
            continue
        already = BundleRuleAssociation.query.filter_by(
            bundle_id=bundle.id, rule_id=rule.id,
        ).first()
        if already is None:
            db.session.add(BundleRuleAssociation(bundle_id=bundle.id, rule_id=rule.id))
            added += 1
    return added


def _upsert_bundle(connector: Connector, shadow_user_id: int, remote: dict,
                   mode: str = 'soft', triggered_by_id: int = None) -> str:
    """Create or update a Bundle from a remote payload dict, then attach the
    local rules listed in remote['rules'] (rules are pulled before bundles,
    so they already exist locally when sync_rules is enabled).
    Returns 'created', 'updated', 'skipped', 'unchanged', or 'invalid'.
    """
    remote_uuid = remote.get('uuid')
    if not remote_uuid:
        return 'invalid'

    owner_id = triggered_by_id if (mode == 'hard' and triggered_by_id) else shadow_user_id

    existing = Bundle.query.filter_by(
        connector_id=connector.id,
        remote_bundle_uuid=remote_uuid,
    ).first()

    now = datetime.datetime.now(datetime.timezone.utc)

    if existing:
        # Always repair membership, even when the bundle itself is untouched
        added = _sync_bundle_rules(existing, remote.get('rules', []))
        if mode == 'soft':
            return 'updated' if added else 'skipped'
        remote_ts = remote.get('updated_at')
        if remote_ts and existing.updated_at:
            try:
                remote_dt = datetime.datetime.fromisoformat(remote_ts.replace('Z', '+00:00')).replace(tzinfo=None)
                if remote_dt <= existing.updated_at:
                    return 'updated' if added else 'unchanged'
            except ValueError:
                pass
        # Only update content fields, keep metadata
        existing.name        = remote.get('name', existing.name)
        existing.description = remote.get('description', existing.description)
        existing.user_id     = owner_id
        existing.updated_at  = now
        return 'updated'

    bundle = Bundle(
        uuid=str(uuid_mod.uuid4()),
        remote_bundle_uuid=remote_uuid,
        connector_id=connector.id,
        user_id=owner_id,
        name=remote.get('name', ''),
        description=remote.get('description'),
        created_by='connector',
        access=True,
        vote_up=0,
        vote_down=0,
        created_at=now,
        updated_at=now,
    )
    db.session.add(bundle)
    db.session.flush()
    _sync_bundle_rules(bundle, remote.get('rules', []))
    return 'created'
