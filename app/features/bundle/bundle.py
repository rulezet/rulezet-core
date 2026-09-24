from flask import Blueprint, abort, flash, jsonify, redirect, render_template , request, url_for
from flask_login import current_user, login_required

from app.features.bundle.bundle_form import AddNewBundleForm, EditBundleForm
from app.core.utils.utils import form_to_dict, safe_referrer
from app.features.misp.bundle.misp_object import get_bundle_misp_event
from . import bundle_core as BundleModel
from .bundle_history_core import track_bundle_change, get_bundle_history_page, get_bundle_history_entry, diff_snapshots as diff_bundle_snapshots
from ..rule import rule_core as RuleModel
from ..account import account_core as AccountModel
from app.core.utils.activity_log import log_activity

from app import db
import io
import re
import zipfile
import json
from flask import send_file

#############
#   Bundle  #
#############

bundle_blueprint = Blueprint(
    'bundle',
    __name__,
    template_folder='templates',    
    static_folder='static'
)

#############
#   Create  #
#############

@bundle_blueprint.route("/create", methods=['GET' , 'POST'])
@login_required
def create():     
    """Create a bundle with form"""     
    form = AddNewBundleForm()
    if form.validate_on_submit():
        form_dict = form_to_dict(form)
        
        my_bundle = BundleModel.create_bundle(form_dict, current_user)
        if my_bundle:
            log_activity("bundle.create", f"Created bundle '{my_bundle.name}'",
                         target_type="bundle", target_id=my_bundle.id, target_uuid=my_bundle.uuid,
                         is_public=bool(my_bundle.access))
            profil_game_user = AccountModel.get_or_create_gamification_profile(current_user.id)
            if profil_game_user:
                AccountModel.update_bundles_owned_gamification(profil_game_user.id, current_user.id)
            flash('Bundle created !', 'success')
            return redirect(url_for("bundle.edit", bundle_id=my_bundle.id))
        else:
            flash('Error to create', 'danger')
            return render_template("bundle/create_bundle.html", form=form)
        
    return render_template("bundle/create_bundle.html", form=form)


############
#   List   #
############

@bundle_blueprint.route("/list", methods=['GET' , 'POST'])
def list() :     
    """list all bundles"""     
    return render_template("bundle/list_bundle.html" )

@bundle_blueprint.route("/get_all_bundles", methods=['GET'])
def get_all_bundles():     
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', type=str)
    
    # Existing Tags Logic
    # dans la route
    tag_names_raw = request.args.get('tag_ids', type=str)
    tag_name_list = [t.strip() for t in tag_names_raw.split(',') if t.strip()] if tag_names_raw else []

    # New Vulnerability Logic
    vuln_raw = request.args.get('vulnerabilities', type=str)
    vuln_list = [v.strip() for v in vuln_raw.split(',') if v.strip()] if vuln_raw else []
    own = request.args.get('own', type=str)
    own = True if own == '1' else False 

    # Pass vuln_list to the model method
    bundles_pagination = BundleModel.get_all_bundles_page(page, search, own, tag_name_list, vuln_list)
    
    return {
        "bundle_list_": [r.to_json() for r in bundles_pagination.items],
        "total_pages": bundles_pagination.pages, 
        "total_bundles": bundles_pagination.total
    }, 200

############
#  action  #
############

@bundle_blueprint.route("/delete", methods=['POST'])  # state-changing: POST + CSRF (was GET)
@login_required
def delete() :     
    """Delete a bundle"""     
    bundle_id = request.args.get('id', 1, type=int)
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {"success": False, "message": "Bundle not found", "toast_class": "danger-subtle"}, 404
    if current_user.id == bundle.user_id or current_user.is_admin():
        bundle_name = bundle.name
        bundle_uuid = bundle.uuid
        success_ = BundleModel.delete_bundle(bundle_id)
        if success_:
            log_activity("bundle.delete", f"Deleted bundle '{bundle_name}' (id={bundle_id})",
                         target_type="bundle", target_id=bundle_id, target_uuid=bundle_uuid)
            return {"success": True,
                    "message": "Bundle deleted !",
                    "toast_class" : "success-subtle"}, 200
        return {"success": False, 
                    "message": "Deleted fail  !", 
                    "toast_class" : "danger-subtle"}, 500
    else:
        return {"success": False, 
                "message": "You don't have the permission to do that !", 
                "toast_class" : "danger-subtle"}, 401
    

@bundle_blueprint.route("/edit/<int:bundle_id>", methods=['GET' , 'POST'])
@login_required
def edit(bundle_id) :     
    """Edit a bundle"""     
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return render_template("404.html"), 404
    if current_user.id == bundle.user_id or current_user.is_admin():
        form = EditBundleForm(bundle_id=bundle_id)
        if form.validate_on_submit():
            form_dict = form_to_dict(form)
            v_data = request.form.get('vulnerabilities')
            form_dict['vulnerabilities'] = v_data
            
            BundleModel.update_bundle(bundle_id , form_dict )
            log_activity("bundle.edit", f"Edited bundle '{bundle.name}' (id={bundle_id})",
                         target_type="bundle", target_id=bundle_id, target_uuid=bundle.uuid,
                         is_public=bool(bundle.access))
            flash("Bundle modified with success!", "success")
            return redirect(safe_referrer())
        else:
            form.description.data = bundle.description
            form.name.data = bundle.name 
            form.public.data = bundle.access

        return render_template("bundle/edit_bundle.html", form=form, bundle=bundle)
    else:
        return render_template("access_denied.html"), 403
    
@bundle_blueprint.route("/detail/<int:bundle_id>", methods=['GET'])
def detail(bundle_id) :     
    """Go to detail of a bundle"""    
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if bundle: 
        resp = _apply_share_param(bundle)
        if resp is not None:
            return resp
        if _can_view_bundle(bundle):
            return _no_referrer_leak(render_template("bundle/detail_bundle.html", bundle_id=bundle_id, bundle_name=bundle.name,
                                   via_share_link=not bundle.access and not _is_bundle_manager(bundle)))
        else:
            return render_template("access_denied.html"),403
    else:
        return render_template("404.html"), 404

@bundle_blueprint.route("/detail/<string:bundle_uuid>", methods=['GET'])
def detail_uuid(bundle_uuid) :
    """Go to detail of a bundle"""
    bundle = BundleModel.get_bundle_by_uuid(bundle_uuid)
    if bundle:
        resp = _apply_share_param(bundle)
        if resp is not None:
            return resp
        if _can_view_bundle(bundle):
            return _no_referrer_leak(render_template("bundle/detail_bundle.html", bundle_id=bundle.id, bundle_name=bundle.name,
                                   via_share_link=not bundle.access and not _is_bundle_manager(bundle)))
        else:
            return render_template("access_denied.html"),403
    else:
        return render_template("404.html"), 404
    

@bundle_blueprint.route("/get_all_rule", methods=['GET'])
def get_all_rule() :     
    """get all rule for a bundle"""     
    rules = RuleModel.get_rules()
    if rules:
        return {"success": True, 
                "rules": [r.to_json() for r in rules], 
                "toast_class" : "success"}, 200
    return {"success": False, 
                "message": "Deleted fail  !", 
                "toast_class" : "danger"}, 500
# -----------------------------------------------------------------------------------------------------------------------------
@bundle_blueprint.route("/save_workspace/<int:bundle_id>", methods=['POST'])
@login_required
def save_workspace(bundle_id):
    data = request.json
    structure = data.get('structure') # The tree from Vue.js

    if not bundle_id:
        return {"success": False, "toast_class": "danger", "message": "Missing bundle_id or structure"}, 500
    
    # Check if the bundle exists
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {"success": False, "toast_class": "danger", "message": "Bundle not found"}, 404
    
    # Check if the user has permission to save the workspace
    if current_user.id != bundle.user_id and not current_user.is_admin():
        return {"success": False, "toast_class": "danger", "message": "You don't have the permission to do that!"}, 401

    error = BundleModel.validate_structure(structure)
    if error:
        return {"success": False, "toast_class": "danger-subtle", "message": error}, 400

    # Both steps rewrite the bundle's rules/tree — tracked as one history
    # entry (coalesced across the editor's autosaves, see bundle_history_core).
    with track_bundle_change(bundle_id, "structure", user=current_user):
        s = BundleModel.update_bundle_from_structure(bundle_id, structure)
        if not s:
            return {"success": False, "toast_class": "danger", "message": "Error updating rule view count"}, 500
        success = BundleModel.save_workspace(bundle_id, structure)

    if success:
        log_activity(
            "bundle.edit",
            f"Saved workspace structure for bundle id={bundle_id}",
            target_type="bundle", target_id=bundle_id,
            extra={"action": "save_workspace"},
            is_public=False,
        )
        return {"success": True, "toast_class": "success", "message": "Workspace saved successfully"}, 200
    else:
        return {"success": False, "toast_class": "danger", "message": "Error saving workspace"}, 500

def _can_view_bundle(bundle):
    return BundleModel.can_view_bundle(bundle)


def _is_bundle_manager(bundle):
    return current_user.is_authenticated and (current_user.id == bundle.user_id or current_user.is_admin())


# ── Private share link ────────────────────────────────────────────────────

def _share_url(token):
    bundle = BundleModel.Bundle.query.filter_by(share_token=token).first() if token else None
    if bundle is None:
        return url_for("bundle.open_shared_bundle", token=token, _external=True)
    # The detail URL itself carries the key (?share=…) — opening it grants
    # access (after login) and the key stays visible in the address bar.
    return url_for("bundle.detail", bundle_id=bundle.id, share=token, _external=True)


@bundle_blueprint.route("/share/<string:token>", methods=['GET'])
@login_required
def open_shared_bundle(token):
    """Share link entry point: needs an account; grants this session access
    to the (private) bundle, then lands on its detail page."""
    bundle = BundleModel.grant_share_access(token)
    if not bundle:
        flash("This share link is invalid or has been revoked.", "danger")
        return render_template("access_denied.html"), 403
    # (logged by _apply_share_param on the detail page — the activity log
    # stores the request path, and this path contains the key)
    # Keep the key visible in the URL: the page itself shows it was reached
    # through a share link, and the URL keeps working on its own.
    return redirect(url_for("bundle.detail", bundle_id=bundle.id, share=token))


def _apply_share_param(bundle):
    """`?share=<token>` on a detail URL: grant access like /bundle/share/<token>.
    Returns a redirect to the login page when the visitor isn't logged in
    (a share link always requires an account), else None."""
    token = request.args.get("share", type=str)
    if not token or bundle.access:
        return None
    if not current_user.is_authenticated:
        return redirect(url_for("account.login", next=request.full_path))
    granted = BundleModel.grant_share_access(token)   # unknown/revoked token → nothing granted
    if granted is not None and granted.id == bundle.id and not _is_bundle_manager(bundle):
        # request path = /bundle/detail/<id> — the key (query string) is not logged
        log_activity("bundle.share_open", f"Opened bundle '{bundle.name}' via share link",
                     target_type="bundle", target_id=bundle.id, target_uuid=bundle.uuid, is_public=False)
    return None


def _no_referrer_leak(resp):
    """Bundle pages can carry ?share=<key> — never send it in a Referer."""
    from flask import make_response
    resp = make_response(resp)
    resp.headers["Referrer-Policy"] = "same-origin"
    return resp


@bundle_blueprint.route("/<int:bundle_id>/share", methods=['GET'])
@login_required
def get_share_link(bundle_id):
    """Owner/admin: current share link (or none)."""
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {"success": False, "message": "Bundle not found", "toast_class": "danger"}, 404
    if not _is_bundle_manager(bundle):
        return {"success": False, "message": "Only the owner or an admin can manage the share link", "toast_class": "danger"}, 403
    return {
        "success": True,
        "url": _share_url(bundle.share_token) if bundle.share_token else None,
        "created_at": bundle.share_token_created_at.strftime('%Y-%m-%d %H:%M') if bundle.share_token_created_at else None,
        "is_public": bool(bundle.access),
    }, 200


@bundle_blueprint.route("/<int:bundle_id>/share", methods=['POST'])
@login_required
def regenerate_share_link(bundle_id):
    """Owner/admin: create or regenerate the share link (old one stops working)."""
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {"success": False, "message": "Bundle not found", "toast_class": "danger"}, 404
    if not _is_bundle_manager(bundle):
        return {"success": False, "message": "Only the owner or an admin can manage the share link", "toast_class": "danger"}, 403
    had_link = bool(bundle.share_token)
    token = BundleModel.regenerate_share_token(bundle_id)
    if not token:
        return {"success": False, "message": "Could not create the share link", "toast_class": "danger"}, 500
    log_activity("bundle.share_regenerate" if had_link else "bundle.share_create",
                 f"{'Regenerated' if had_link else 'Created'} share link for bundle '{bundle.name}'",
                 target_type="bundle", target_id=bundle.id, target_uuid=bundle.uuid, is_public=False)
    return {
        "success": True,
        "url": _share_url(token),
        "message": "Share link regenerated — the previous link no longer works" if had_link else "Share link created",
        "toast_class": "success-subtle",
    }, 200


@bundle_blueprint.route("/<int:bundle_id>/share", methods=['DELETE'])
@login_required
def revoke_share_link(bundle_id):
    """Owner/admin: revoke the share link."""
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {"success": False, "message": "Bundle not found", "toast_class": "danger"}, 404
    if not _is_bundle_manager(bundle):
        return {"success": False, "message": "Only the owner or an admin can manage the share link", "toast_class": "danger"}, 403
    BundleModel.revoke_share_token(bundle_id)
    log_activity("bundle.share_revoke", f"Revoked share link for bundle '{bundle.name}'",
                 target_type="bundle", target_id=bundle.id, target_uuid=bundle.uuid, is_public=False)
    return {"success": True, "message": "Share link revoked", "toast_class": "success-subtle"}, 200


@bundle_blueprint.route("/history/<int:bundle_id>", methods=['GET'])
def bundle_history(bundle_id):
    """Paginated change history of a bundle (History tab)."""
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {"success": False, "message": "Bundle not found", "toast_class": "danger"}, 404
    if not _can_view_bundle(bundle):
        return {"success": False, "message": "Access denied", "toast_class": "danger"}, 403

    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 10, type=int), 5), 50)
    pagination = get_bundle_history_page(bundle_id, page=page, per_page=per_page)
    entries = []
    for h in pagination.items:
        e = h.to_json()
        # Re-derive the readable diff from the stored snapshots so older rows
        # benefit from display improvements (e.g. description excerpts).
        if h.old_snapshot and h.new_snapshot:
            e["changes"] = diff_bundle_snapshots(h.old_snapshot, h.new_snapshot)
        entries.append(e)

    # Bundles created before history existed: synthesize their creation
    # event at the very end of the timeline so it never starts empty.
    is_last_page = page >= max(pagination.pages, 1)
    if is_last_page and not any(e["action"] == "created" for e in entries) \
            and not bundle.history.filter_by(action="created").first():
        owner = bundle.user
        entries.append({
            "id": None, "uuid": f"created-{bundle.uuid}", "bundle_id": bundle.id,
            "user_id": bundle.user_id,
            "user_name": owner.first_name if owner else None,
            "user_avatar": owner.get_avatar_url() if owner else None,
            "action": "created", "summary": "Bundle created", "changes": [],
            "created_at": bundle.created_at.strftime('%Y-%m-%dT%H:%M:%S') + 'Z',
            "updated_at": None, "has_description_diff": False, "synthetic": True,
        })

    return jsonify({
        "success": True,
        "entries": entries,
        "page": page,
        "pages": pagination.pages,
        "total": pagination.total + (1 if entries and entries[-1].get("synthetic") else 0),
    }), 200


@bundle_blueprint.route("/history/<int:bundle_id>/<int:entry_id>", methods=['GET'])
def bundle_history_entry(bundle_id, entry_id):
    """One history entry with the full old/new description (for the diff view)."""
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {"success": False, "message": "Bundle not found", "toast_class": "danger"}, 404
    if not _can_view_bundle(bundle):
        return {"success": False, "message": "Access denied", "toast_class": "danger"}, 403
    entry = get_bundle_history_entry(bundle_id, entry_id)
    if not entry:
        return {"success": False, "message": "History entry not found", "toast_class": "danger"}, 404
    return jsonify({"success": True, "entry": entry.to_json(include_descriptions=True)}), 200


@bundle_blueprint.route("/<int:bundle_id>/rule_content/<int:rule_id>", methods=['GET'])
def bundle_rule_content(bundle_id, rule_id):
    """Content of one rule of the bundle (lazy-loaded by the viewer / editor)."""
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {"success": False, "message": "Bundle not found", "toast_class": "danger"}, 404
    if not BundleModel.can_view_bundle(bundle):
        return {"success": False, "message": "Access denied", "toast_class": "danger"}, 403
    rel, err = _requested_release(bundle_id)
    if err:
        return err
    if rel is not None:
        # frozen content — works even if the rule was edited or deleted since
        r = (rel.snapshot.get("rules") or {}).get(str(rule_id))
        if not r:
            return {"success": False, "message": "Rule not in this release", "toast_class": "danger"}, 404
        return {"success": True, "rule_id": rule_id, "uuid": r["uuid"], "title": r["title"],
                "format": r["format"], "content": r["content"], "release": rel.version}, 200
    rule = BundleModel.get_rule_content_in_bundle(bundle_id, rule_id)
    if not rule:
        return {"success": False, "message": "Rule not found in this bundle", "toast_class": "danger"}, 404
    return {"success": True, "rule_id": rule.id, "uuid": rule.uuid, "title": rule.title,
            "format": rule.format or "", "content": rule.to_string or ""}, 200


def _mark_editable_items(health, bundle):
    """Flag each finding with can_edit — the bundle's owner or an admin can
    jump to the bundle editor with that rule selected in the structure."""
    if not health:
        return
    manager = _is_bundle_manager(bundle)
    for c in health["checks"]:
        for i in c["items"]:
            i["can_edit"] = bool(manager and i.get("rule_id"))


# ── Community notes / known issues ────────────────────────────────────────
# Rules:
#   read      anyone who can view the bundle (public, owner/admin, share link)
#   create    logged-in + can view + the bundle is PUBLIC (owner/admin always)
#   edit      the note's author (while they can still view the bundle) or owner/admin
#   resolve   owner/admin
#   delete    the note's author (while they can view the bundle) or owner/admin
# So when a bundle goes private, a note's author loses access to their own
# note — they get it back only through the bundle's share link.

NOTE_SEVERITIES = ("info", "warning", "critical")

# Only these taxonomies make sense on a note ("this rule false-positives on…",
# "needs review", "low confidence"…) — every other tag is refused.
NOTE_TAG_PREFIXES = (
    "false-positive:",                  # risk / confirmed
    "use-case-applicability:",          # bad IOC / rule pattern, rule config error, test alert…
    "incident-disposition:",            # faulty indicator, duplicate…
    "misp-workflow:analysis=",          # false-positive, highly-likely-positive…
    "workflow:",                        # todo / state
    "priority-level:",                  # how urgent the fix is
    "detection-engineering:",
    "hunt-ex:",                         # data-source / detection gaps, environment-specific
    "cti-evaluation:",                  # accuracy, clarity…
    "estimative-language:",             # confidence / likelihood
    "admiralty-scale:",                 # source reliability
    "information-origin:",              # AI-generated / human-generated
    "ioc:",                             # artifact-state
)
NOTE_MAX_TAGS = 8
NOTE_MAX_PER_HOUR = 10          # per user, per bundle
NOTE_MAX_MENTIONS = 10          # users notified per note / edit
_pylist = type([])     # the builtin — `list` is shadowed in this module by the /list route view


def _note_tag_allowed(name):
    return (name or "").lower().startswith(NOTE_TAG_PREFIXES)


def _note_tags_from_request(data):
    """Validated Tag objects for data['tag_ids'] — (tags, error)."""
    from app.core.db_class.db import Tag
    raw = data.get("tag_ids")
    if raw is None:
        return None, None                          # not sent → leave the note's tags alone
    if not isinstance(raw, _pylist) or len(raw) > NOTE_MAX_TAGS:
        return None, f"At most {NOTE_MAX_TAGS} tags per note"
    try:
        ids = {int(x) for x in raw}
    except (TypeError, ValueError):
        return None, "Invalid tag"
    tags = Tag.query.filter(Tag.id.in_(ids), Tag.is_active == True).all() if ids else []
    if len(tags) != len(ids) or not all(_note_tag_allowed(t.name) for t in tags):
        return None, "This tag can't be used on a note — only false-positive / applicability / workflow / confidence-style taxonomies are allowed"
    return tags, None


def _set_note_tags(note, tags):
    from app.core.db_class.db import BundleNoteTag
    if tags is None:
        return
    wanted = {t.id for t in tags}
    for a in _pylist(note.tag_assocs):
        if a.tag_id not in wanted:
            note.tag_assocs.remove(a)
    have = {a.tag_id for a in note.tag_assocs}
    for t in tags:
        if t.id not in have:
            note.tag_assocs.append(BundleNoteTag(tag_id=t.id))


@bundle_blueprint.route("/note_tags", methods=['GET'])
def search_note_tags():
    """Tags usable on a bundle note (curated taxonomies only), searchable."""
    from sqlalchemy import or_
    from app.core.db_class.db import Tag
    q = (request.args.get("q") or "").strip()
    query = Tag.query.filter(Tag.is_active == True,
                             or_(*[Tag.name.ilike(p + "%") for p in NOTE_TAG_PREFIXES]))
    if q:
        query = query.filter(Tag.name.ilike(f"%{q}%"))
    order = db.case(*[(Tag.name.ilike(p + "%"), i) for i, p in enumerate(NOTE_TAG_PREFIXES)], else_=99)
    tags = query.order_by(order, Tag.name).limit(40).all()
    return jsonify({"success": True, "prefixes": [*NOTE_TAG_PREFIXES],
                    "tags": [{"id": t.id, "name": t.name, "color": t.color, "description": t.description} for t in tags]}), 200
_MENTION_RE = re.compile(r"@\[[^\]]+\]\((\d+)\)")


def _mentioned_ids(text):
    return {int(x) for x in _MENTION_RE.findall(text or "")}


def _notify_note_mentions(bundle, note, previous_text=""):
    """Notify users @mentioned in a note — only newly mentioned ones, and only
    if they can see the bundle (public, or owner / admin of a private one —
    share-link holders can't be known server-side and the key is never sent
    in a notification). Returns the ids that could NOT be notified."""
    from app.core.db_class.db import User
    from app.features.notification.notification_core import notify_user_mentioned
    new_ids = _mentioned_ids(note.content) - _mentioned_ids(previous_text) - {current_user.id}
    skipped = []
    for uid in sorted(new_ids)[:NOTE_MAX_MENTIONS]:
        u = db.session.get(User, uid)
        if not u:
            continue
        if not (bundle.access or u.id == bundle.user_id or u.is_admin()):
            skipped.append(u.id)
            continue
        try:
            notify_user_mentioned(u.id, current_user.id, f"note '{note.title}' on bundle '{bundle.name}'",
                                  f"/bundle/detail/{bundle.id}#notes")
        except Exception:
            pass
    return skipped


def _note_guard(bundle_id, write=False):
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return None, ({"success": False, "message": "Bundle not found", "toast_class": "danger"}, 404)
    if not BundleModel.can_view_bundle(bundle):
        return None, ({"success": False, "message": "Access denied", "toast_class": "danger"}, 403)
    if write and not current_user.is_authenticated:
        return None, ({"success": False, "message": "Log in to write a note", "toast_class": "danger"}, 401)
    return bundle, None


def _note_payload():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    severity = (data.get("severity") or "warning").strip().lower()
    if not (3 <= len(title) <= 200):
        return None, "The title must be 3–200 characters"
    if not (1 <= len(content) <= 20000):
        return None, "The note must be 1–20,000 characters"
    if severity not in NOTE_SEVERITIES:
        return None, "Invalid severity"
    return {"title": title, "content": content, "severity": severity}, None


@bundle_blueprint.route("/<int:bundle_id>/notes", methods=['GET'])
def list_bundle_notes(bundle_id):
    from app.core.db_class.db import BundleNote
    bundle, err = _note_guard(bundle_id)
    if err:
        return err
    notes = (BundleNote.query.filter_by(bundle_id=bundle_id)
             .order_by(db.case((BundleNote.status == 'open', 0), else_=1),
                       db.case((BundleNote.severity == 'critical', 0), (BundleNote.severity == 'warning', 1), else_=2),
                       BundleNote.created_at.desc()).all())
    me = current_user.id if current_user.is_authenticated else None
    manager = _is_bundle_manager(bundle)
    out = []
    for n in notes:
        j = n.to_json()
        j["can_edit"] = bool(me and (n.user_id == me or manager))
        j["can_delete"] = j["can_edit"]
        j["can_resolve"] = manager
        out.append(j)
    return jsonify({
        "success": True, "notes": out,
        "open": sum(1 for n in notes if n.status == "open"),
        "can_create": bool(me and (bundle.access or manager)),
        "create_blocked_reason": None if (bundle.access or manager) else "Notes can only be added while the bundle is public.",
    }), 200


@bundle_blueprint.route("/<int:bundle_id>/notes", methods=['POST'])
@login_required
def create_bundle_note(bundle_id):
    import uuid as _uuid
    from app.core.db_class.db import BundleNote
    bundle, err = _note_guard(bundle_id, write=True)
    if err:
        return err
    if not bundle.access and not _is_bundle_manager(bundle):
        return {"success": False, "message": "Notes can only be added while the bundle is public", "toast_class": "danger-subtle"}, 403
    import datetime as _dt
    recent = BundleNote.query.filter(BundleNote.bundle_id == bundle_id, BundleNote.user_id == current_user.id,
                                     BundleNote.created_at >= _dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=1)).count()
    if recent >= NOTE_MAX_PER_HOUR and not _is_bundle_manager(bundle):
        return {"success": False, "message": "Too many notes on this bundle in the last hour — try again later",
                "toast_class": "warning-subtle"}, 429
    payload, error = _note_payload()
    if error:
        return {"success": False, "message": error, "toast_class": "danger-subtle"}, 400
    tags, error = _note_tags_from_request(request.get_json(silent=True) or {})
    if error:
        return {"success": False, "message": error, "toast_class": "danger-subtle"}, 400
    note = BundleNote(uuid=str(_uuid.uuid4()), bundle_id=bundle_id, user_id=current_user.id, **payload)
    db.session.add(note)
    _set_note_tags(note, tags)
    db.session.commit()
    skipped = _notify_note_mentions(bundle, note)
    log_activity("bundle.note_create", f"Added a note on bundle '{bundle.name}': {note.title}",
                 target_type="bundle", target_id=bundle.id, target_uuid=bundle.uuid, is_public=bool(bundle.access))
    msg = "Note published"
    if skipped:
        msg += f" — {len(skipped)} mentioned user(s) can't see this private bundle and were not notified"
    return {"success": True, "note": note.to_json(), "message": msg, "toast_class": "success-subtle",
            "not_notified": skipped}, 201


def _own_note_or_error(bundle, note_id, need="edit"):
    from app.core.db_class.db import BundleNote
    note = BundleNote.query.filter_by(bundle_id=bundle.id, id=note_id).first()
    if not note:
        return None, ({"success": False, "message": "Note not found", "toast_class": "danger"}, 404)
    manager = _is_bundle_manager(bundle)
    allowed = manager if need == "resolve" else (manager or note.user_id == current_user.id)
    if not allowed:
        return None, ({"success": False, "message": "You can't change this note", "toast_class": "danger"}, 403)
    return note, None


@bundle_blueprint.route("/<int:bundle_id>/notes/<int:note_id>", methods=['PUT'])
@login_required
def update_bundle_note(bundle_id, note_id):
    import datetime as _dt
    bundle, err = _note_guard(bundle_id, write=True)
    if err:
        return err
    note, err = _own_note_or_error(bundle, note_id)
    if err:
        return err
    payload, error = _note_payload()
    if error:
        return {"success": False, "message": error, "toast_class": "danger-subtle"}, 400
    tags, error = _note_tags_from_request(request.get_json(silent=True) or {})
    if error:
        return {"success": False, "message": error, "toast_class": "danger-subtle"}, 400
    previous = note.content
    _set_note_tags(note, tags)
    for k, v in payload.items():
        setattr(note, k, v)
    note.updated_at = _dt.datetime.now(_dt.timezone.utc)
    db.session.commit()
    skipped = _notify_note_mentions(bundle, note, previous_text=previous)
    msg = "Note updated" + (f" — {len(skipped)} mentioned user(s) can't see this private bundle and were not notified" if skipped else "")
    return {"success": True, "note": note.to_json(), "message": msg, "toast_class": "success-subtle",
            "not_notified": skipped}, 200


@bundle_blueprint.route("/<int:bundle_id>/notes/<int:note_id>/status", methods=['POST'])
@login_required
def set_bundle_note_status(bundle_id, note_id):
    import datetime as _dt
    bundle, err = _note_guard(bundle_id, write=True)
    if err:
        return err
    note, err = _own_note_or_error(bundle, note_id, need="resolve")
    if err:
        return err
    status = ((request.get_json(silent=True) or {}).get("status") or "").lower()
    if status not in ("open", "resolved"):
        return {"success": False, "message": "Invalid status", "toast_class": "danger-subtle"}, 400
    note.status = status
    note.resolved_by_id = current_user.id if status == "resolved" else None
    note.resolved_at = _dt.datetime.now(_dt.timezone.utc) if status == "resolved" else None
    db.session.commit()
    return {"success": True, "note": note.to_json(),
            "message": "Marked as resolved" if status == "resolved" else "Reopened", "toast_class": "success-subtle"}, 200


@bundle_blueprint.route("/<int:bundle_id>/notes/<int:note_id>", methods=['DELETE'])
@login_required
def delete_bundle_note(bundle_id, note_id):
    bundle, err = _note_guard(bundle_id, write=True)
    if err:
        return err
    note, err = _own_note_or_error(bundle, note_id)
    if err:
        return err
    db.session.delete(note)
    db.session.commit()
    return {"success": True, "message": "Note deleted", "toast_class": "success-subtle"}, 200


@bundle_blueprint.route("/<int:bundle_id>/health/fix", methods=['POST'])
@login_required
def bundle_health_fix(bundle_id):
    """Apply one "Fix it for me" action from the Health tab (owner / admin)."""
    from .bundle_health_fix_core import apply_fix
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {"success": False, "message": "Bundle not found", "toast_class": "danger"}, 404
    if not _is_bundle_manager(bundle):
        return {"success": False, "message": "Only the owner or an admin can fix the bundle", "toast_class": "danger"}, 403
    fix = (request.get_json(silent=True) or {}).get("fix")
    ok, message = apply_fix(bundle_id, fix, current_user)
    if ok:
        log_activity("bundle.health_fix", f"Health fix on bundle '{bundle.name}': {message}",
                     target_type="bundle", target_id=bundle.id, target_uuid=bundle.uuid,
                     extra={"fix": {k: fix.get(k) for k in ("action", "rule_id", "near_rule_id", "node_id", "tag")
                                    if isinstance(fix, dict) and fix.get(k) is not None}},
                     is_public=False)
    return {"success": ok, "message": message, "toast_class": "success-subtle" if ok else "danger-subtle"}, (200 if ok else 400)


@bundle_blueprint.route("/<int:bundle_id>/health", methods=['GET'])
def bundle_health_report(bundle_id):
    """Pre-deployment checks for the bundle (Health tab)."""
    from .bundle_health_core import bundle_health
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {"success": False, "message": "Bundle not found", "toast_class": "danger"}, 404
    if not BundleModel.can_view_bundle(bundle):
        return {"success": False, "message": "Access denied", "toast_class": "danger"}, 403
    # ?refresh=1 re-validates every rule (bypasses the syntax cache) — costly,
    # so only the owner / an admin can force it.
    rel, err = _requested_release(bundle_id)
    if err:
        return err
    if rel is not None:
        return jsonify({"success": True, "health": bundle_health(bundle_id, release=rel),
                        "can_rerun": False, "release": rel.version}), 200
    refresh = bool(request.args.get('refresh', type=int))
    if refresh and not _is_bundle_manager(bundle):
        return {"success": False, "message": "Only the owner or an admin can re-run the checks", "toast_class": "danger-subtle"}, 403
    health = bundle_health(bundle_id, refresh=refresh)
    _mark_editable_items(health, bundle)
    if _is_bundle_manager(bundle):
        from .bundle_health_fix_core import attach_fixes
        attach_fixes(health, bundle_id)
    return jsonify({"success": True, "health": health,
                    "can_rerun": _is_bundle_manager(bundle)}), 200


# ── Releases (versioned, frozen) ──────────────────────────────────────────

def _release_guard(bundle_id, manage=False):
    """(bundle, error_response) — read access for everyone who can view,
    owner/admin for publishing/deleting."""
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return None, ({"success": False, "message": "Bundle not found", "toast_class": "danger"}, 404)
    if not BundleModel.can_view_bundle(bundle):
        return None, ({"success": False, "message": "Access denied", "toast_class": "danger"}, 403)
    if manage and not _is_bundle_manager(bundle):
        return None, ({"success": False, "message": "Only the owner or an admin can manage releases", "toast_class": "danger"}, 403)
    return bundle, None


def _release_or_current(bundle_id, ref):
    from .bundle_release_core import build_snapshot
    from app.core.db_class.db import BundleRelease
    if ref in (None, "", "current"):
        return "current", build_snapshot(bundle_id)
    rel = BundleRelease.query.filter_by(bundle_id=bundle_id, id=int(ref)).first() if str(ref).isdigit() else None
    return (rel.version, rel.snapshot) if rel else (None, None)


def _requested_release(bundle_id):
    """(release, error_response) for an optional ?release=<id|version>.
    (None, None) when no release is requested (= the live bundle)."""
    from .bundle_release_core import get_release
    ref = request.args.get("release", type=str)
    if not ref:
        return None, None
    rel = get_release(bundle_id, ref)
    if rel is None:
        return None, ({"success": False, "message": f"Release '{ref}' not found", "toast_class": "danger-subtle"}, 404)
    return rel, None


@bundle_blueprint.route("/<int:bundle_id>/releases/<string:ref>/view", methods=['GET'])
def view_bundle_release(bundle_id, ref):
    """Everything the detail page needs to render the bundle *as released*."""
    from .bundle_release_core import get_release, release_view
    bundle, err = _release_guard(bundle_id)
    if err:
        return err
    rel = get_release(bundle_id, ref)
    if rel is None:
        return {"success": False, "message": f"Release '{ref}' not found", "toast_class": "danger-subtle"}, 404
    return jsonify({"success": True, **release_view(rel)}), 200


@bundle_blueprint.route("/<int:bundle_id>/releases", methods=['GET'])
def list_bundle_releases(bundle_id):
    from .bundle_release_core import status_since
    from app.core.db_class.db import BundleRelease
    bundle, err = _release_guard(bundle_id)
    if err:
        return err
    releases = (BundleRelease.query.filter_by(bundle_id=bundle_id)
                .order_by(BundleRelease.created_at.desc(), BundleRelease.id.desc()).all())
    latest_changes = status_since(releases[0]) if releases else None
    return jsonify({
        "success": True,
        "releases": [r.to_json() for r in releases],
        "latest_changes": latest_changes,
        "can_manage": _is_bundle_manager(bundle),
    }), 200


@bundle_blueprint.route("/<int:bundle_id>/releases/draft", methods=['GET'])
@login_required
def draft_bundle_release(bundle_id):
    from .bundle_release_core import draft_release
    bundle, err = _release_guard(bundle_id, manage=True)
    if err:
        return err
    return jsonify({"success": True, **draft_release(bundle_id)}), 200


@bundle_blueprint.route("/<int:bundle_id>/releases", methods=['POST'])
@login_required
def create_bundle_release(bundle_id):
    from .bundle_release_core import create_release
    bundle, err = _release_guard(bundle_id, manage=True)
    if err:
        return err
    data = request.get_json(silent=True) or {}
    rel, error = create_release(bundle_id, current_user, data.get("version"), data.get("title"), data.get("notes"))
    if error:
        return {"success": False, "message": error, "toast_class": "danger-subtle"}, 400
    log_activity("bundle.release", f"Published release {rel.version} of bundle '{bundle.name}'",
                 target_type="bundle", target_id=bundle.id, target_uuid=bundle.uuid, is_public=bool(bundle.access))
    return {"success": True, "release": rel.to_json(),
            "message": f"Release {rel.version} published", "toast_class": "success-subtle"}, 201


@bundle_blueprint.route("/<int:bundle_id>/releases/<int:release_id>", methods=['DELETE'])
@login_required
def delete_bundle_release(bundle_id, release_id):
    from app.core.db_class.db import BundleRelease
    bundle, err = _release_guard(bundle_id, manage=True)
    if err:
        return err
    rel = BundleRelease.query.filter_by(bundle_id=bundle_id, id=release_id).first()
    if not rel:
        return {"success": False, "message": "Release not found", "toast_class": "danger"}, 404
    version = rel.version
    db.session.delete(rel)
    db.session.commit()
    log_activity("bundle.release_delete", f"Deleted release {version} of bundle '{bundle.name}'",
                 target_type="bundle", target_id=bundle.id, target_uuid=bundle.uuid, is_public=False)
    return {"success": True, "message": f"Release {version} deleted", "toast_class": "success-subtle"}, 200


@bundle_blueprint.route("/<int:bundle_id>/releases/<int:release_id>/changes", methods=['GET'])
def bundle_release_changes(bundle_id, release_id):
    """What differs between this release and `against` (another release id, or 'current')."""
    from .bundle_release_core import compare_snapshots, changelog_markdown
    bundle, err = _release_guard(bundle_id)
    if err:
        return err
    base_label, base = _release_or_current(bundle_id, release_id)
    other_label, other = _release_or_current(bundle_id, request.args.get("against", "current"))
    if base is None or other is None:
        return {"success": False, "message": "Release not found", "toast_class": "danger"}, 404
    diff = compare_snapshots(base, other)
    return jsonify({"success": True, "from": base_label, "to": other_label, "diff": diff,
                    "markdown": changelog_markdown(diff)}), 200


@bundle_blueprint.route("/<int:bundle_id>/releases/<int:release_id>/rule/<int:rule_id>/diff", methods=['GET'])
def bundle_release_rule_diff(bundle_id, release_id, rule_id):
    """Old/new content of one rule between a release and `against` (release id or 'current')."""
    bundle, err = _release_guard(bundle_id)
    if err:
        return err
    base_label, base = _release_or_current(bundle_id, release_id)
    other_label, other = _release_or_current(bundle_id, request.args.get("against", "current"))
    if base is None or other is None:
        return {"success": False, "message": "Release not found", "toast_class": "danger"}, 404
    o = (base.get("rules") or {}).get(str(rule_id))
    n = (other.get("rules") or {}).get(str(rule_id))
    if not o and not n:
        return {"success": False, "message": "Rule not in either version", "toast_class": "danger"}, 404
    return jsonify({"success": True, "rule_id": rule_id, "title": (n or o)["title"], "format": (n or o)["format"],
                    "from": base_label, "to": other_label,
                    "old": (o or {}).get("content", ""), "new": (n or {}).get("content", "")}), 200


@bundle_blueprint.route("/<int:bundle_id>/releases/<int:release_id>/download", methods=['GET'])
def download_bundle_release(bundle_id, release_id):
    from .bundle_release_core import release_zip
    from app.core.db_class.db import BundleRelease
    bundle, err = _release_guard(bundle_id)
    if err:
        return err
    rel = BundleRelease.query.filter_by(bundle_id=bundle_id, id=release_id).first()
    if not rel:
        return {"success": False, "message": "Release not found", "toast_class": "danger"}, 404
    BundleModel.increment_download_count(bundle_id)
    safe_name = "".join(c for c in bundle.name if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_') or "bundle"
    safe_ver = "".join(c for c in rel.version if c.isalnum() or c in ".-_+")
    return send_file(release_zip(rel), as_attachment=True,
                     download_name=f"{safe_name}_{safe_ver}.zip", mimetype='application/zip')


@bundle_blueprint.route("/get_bundle_json/<int:bundle_id>")
def get_bundle_json(bundle_id):
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        abort(404)
    if not BundleModel.can_view_bundle(bundle):
        abort(403)
    # ?full=1 keeps the legacy payload (rule content inlined); default is the
    # light tree — rule content is fetched on demand (rule_content route).
    if request.args.get('full', type=int):
        root_nodes = BundleModel.get_only_root_nodes(bundle_id)
        structure = [node.to_tree_json() for node in root_nodes]
    else:
        structure = BundleModel.build_tree_json(bundle_id)

    # If the bundle is new and empty, return a default root
    if not structure:
        structure = [{"id": "root", "name": "Main Bundle", "type": "folder", "children": []}]

    return jsonify({
        "success": True, 
        "structure": structure
    }), 200
# -----------------------------------------------------------------------------------------------------------------------------
@bundle_blueprint.route("/add_rule_bundle", methods=['POST'])  # state-changing: POST + CSRF (was GET)
@login_required
def add_rule_bundle() :     
    """Add a rule in a bundle"""     
    rule_id = request.args.get('rule_id',  type=int)
    bundle_id = request.args.get('bundle_id', type=int)
    description = request.args.get('description', type=str)

    bundle = BundleModel.get_bundle_by_id(bundle_id)

    if not bundle:
        return {"success": False, "message": "Bundle not found", "toast_class": "danger-subtle"}, 404
    if current_user.id == bundle.user_id or current_user.is_admin():
        if rule_id and bundle_id:
            success_ = BundleModel.add_rule_to_bundle(bundle_id , rule_id , description)
            if success_:
                return {"success": True, 
                        "message": "Rule added  !", 
                        "toast_class" : "success"}, 200
        return {"success": False, 
                    "message": "error no rule or bundle found  !", 
                    "toast_class" : "danger"}, 500
    return {"success": False, 
            "message": "You don't have the permission to do that !", 
            "toast_class" : "danger"}, 401



# update_bundle_tags

@bundle_blueprint.route("/update_bundle_tags/<int:bundle_id>", methods=['POST'])
@login_required
def update_bundle_tags(bundle_id):
    data = request.json
    tag_ids = data.get('tag_ids', [])

    if not bundle_id:
        return {"success": False, "message": "Missing bundle_id"}, 400

    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {"success": False, "message": "Bundle not found"}, 404

    if current_user.id != bundle.user_id and not current_user.is_admin():
        return {"success": False, "message": "You don't have the permission to do that!"}, 401

    success = BundleModel.update_bundle_tags(bundle_id, tag_ids, current_user)
    if success:
        log_activity(
            "bundle.tags_updated",
            f"Updated tags on bundle id={bundle_id} ({len(tag_ids)} tag(s))",
            target_type="bundle", target_id=bundle_id,
            extra={"tag_ids": tag_ids},
            is_public=False,
        )
        return {"success": True, "message": "Tags updated successfully"}, 200
    else:
        return {"success": False, "message": "Error updating tags"}, 500



@bundle_blueprint.route("/remove", methods=['POST'])  # state-changing: POST + CSRF (was GET)
@login_required
def remove() :     
    """Remove a rule in a bundle"""     
    rule_id = request.args.get('rule_id',  type=int)
    bundle_id = request.args.get('bundle_id', type=int)

    bundle = BundleModel.get_bundle_by_id(bundle_id)

    if not bundle:
        return {"success": False, "message": "Bundle not found", "toast_class": "danger-subtle"}, 404
    if current_user.id == bundle.user_id or current_user.is_admin():
        if rule_id and bundle_id:
            success_ = BundleModel.remove_rule_from_bundle(bundle_id , rule_id)
            if success_:
                return {"success": True, 
                        "message": "Rule removed  !", 
                        "toast_class" : "success"}, 200
        return {"success": False, 
                    "message": "error no rule or bundle found  !", 
                    "toast_class" : "danger"}, 500
    return {"success": False, 
            "message": "You don't have the permission to do that !", 
            "toast_class" : "danger"}, 401


@bundle_blueprint.route("/get_rules_page_from_bundle", methods=['GET'])
def get_rules_page_from_bundle() :
    """get all the rule from the bundles for pages"""
    page = request.args.get('page', 1, type=int)
    bundle_id = request.args.get('bundle_id',  type=int)
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        abort(404)
    if not BundleModel.can_view_bundle(bundle):
        abort(403)
    rule_list = BundleModel.get_all_rule_bundles_page(page , bundle_id)
    total_rules = BundleModel.get_total_rule_from_bundle_count(bundle_id)
    if rule_list:
        return {"rules_list": [r.to_json() for r in rule_list],
                "total_pages": rule_list.pages, 
                "total_rules": total_rules,} , 200

    return {"message": "No Rule"} , 200

@bundle_blueprint.route("/get_bundle", methods=['GET'])
def get_bundle():
    """Get a bundle and all its associated rules with full info."""
    bundle_id = request.args.get('bundle_id', type=int)
    if not bundle_id:
        return {
            "message": "Missing bundle_id parameter",
            "success": False
        }, 400

    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {
            "message": f"No bundle found with id {bundle_id}",
            "success": False
        }, 404
    if not BundleModel.can_view_bundle(bundle):
        abort(403)

    rules_ids_from_bundle = BundleModel.get_rule_ids_by_bundle(bundle_id)
    if isinstance(rules_ids_from_bundle, dict) and "error" in rules_ids_from_bundle:
        # no rules or error
        rules_info = []
    else:
        rules_info = []
        for rule_id in rules_ids_from_bundle:
            info = BundleModel.get_full_rule_bundle_info(rule_id)
            if info:
                rules_info.append(info)
    root_nodes = BundleModel.get_only_root_nodes(bundle_id)
    
    # If the bundle is new and empty, return a default root
    if not root_nodes:
        structure = [{"id": "root", "name": "Main Bundle", "type": "folder", "children": []}]
    else:
        structure = [node.to_tree_json() for node in root_nodes]
    return {
        "bundle": bundle.to_json() if hasattr(bundle, 'to_json') else bundle,
        "rules": rules_info,
        "success": True,
        "message": "Bundle and associated rules found",
        "structure": structure
    }, 200


@bundle_blueprint.route("/change_description", methods=['POST'])  # state-changing: POST + CSRF (was GET)
@login_required
def change_description():
    """Chamge the description of the association rule/bundle (the reason to the presence of the rule in the bundle)."""
    association_id = request.args.get('association_id', type=int)
    new_description = request.args.get('new_description', type=str)
    if not association_id:
        return {
            "message": "Missing association_id parameter",
            "success": False,
            "toast_class" : "danger"
        }, 400

    association = BundleModel.get_association_by_id(association_id)
    if not association:
        return {
            "message": f"No association found with id {association_id}",
            "success": False,
            "toast_class" : "danger"
        }, 404
    bundle = BundleModel.get_bundle_by_id(association.bundle_id)

    if not bundle:
        return {"success": False, "message": "Bundle not found", "toast_class": "danger-subtle"}, 404
    if bundle.user_id == current_user.id or current_user.is_admin():
        association.description = new_description
        return {
            "success": True,
            "message": "Description modified with success",
            "toast_class" : "success"
        }, 200
    else:
        return {
            "success": False,
            "message": "Access denied",
            "toast_class" : "danger"
        }, 401

@bundle_blueprint.route("/edit_access", methods=['POST'])  # state-changing: POST + CSRF (was GET)
@login_required
def edit_access():
    """Edit access to a bundle."""
    bundle_id = request.args.get('id', type=int)
    if not bundle_id:
        return {
            "message": "Missing bundle_id parameter",
            "success": False
        }, 400

    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {
            "message": f"No bundle found with id {bundle_id}",
            "success": False
        }, 404

    if not (bundle.user_id == current_user.id or current_user.is_admin()):
        return {
            "success": False,
            "message": "Access denied",
            "toast_class" : "danger"
        }, 401  
    access, message = BundleModel.toggle_bundle_accessibility(bundle_id)
    if access is None:
        return {
            "success": False,
            "message": "Error toggling access",
            "toast_class" : "danger"
        }, 500

    return {
        "success": True,
        "message": f"{message}",
        "new_access": access,
        "toast_class" : "success"
    }, 200


@bundle_blueprint.route("/evaluate", methods=['POST'])  # state-changing: POST + CSRF (was GET)
@login_required
def evaluate():
    """Evaluate a bundle and return aggregated statistics."""
    bundle_id = request.args.get('bundleId', type=int)
    if not bundle_id:
        return {
            "message": "Missing bundle_id parameter",
            "success": False
        }, 400

    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {
            "message": f"No bundle found with id {bundle_id}",
            "success": False
        }, 404
    
    if not BundleModel.can_view_bundle(bundle):
        return {
            "success": False,
            "message": "You don't have the permission to evaluate this bundle",
            "toast_class" : "danger"
        }, 401

    vote_type = request.args.get('voteType', type=str)
    if vote_type not in ['up', 'down']:
        return {
            "message": "Invalid voteType. Must be 'up' or 'down'.",
            "success": False
        }, 400

    already_vote, already_vote_type = BundleModel.has_already_vote(bundle_id, current_user.id)

     # update the gameifcation section
    profil_game_user = AccountModel.get_or_create_gamification_profile(current_user.id)
    if not profil_game_user:
        return jsonify({"message": "Error to update the gamification section"}), 500

    if vote_type == 'up':
        if not already_vote:
            BundleModel.increment_up(bundle_id)
            BundleModel.has_voted('up', bundle_id, current_user.id)

            _ = AccountModel.update_like_gamification(profil_game_user.id, "add_one_to_like")
        elif already_vote_type == 'up':
            BundleModel.remove_one_to_increment_up(bundle_id)
            BundleModel.remove_has_voted('up', bundle_id, current_user.id)

            _ = AccountModel.update_like_gamification(profil_game_user.id, "remove_one_to_like")
        elif already_vote_type == 'down':
            BundleModel.increment_up(bundle_id)
            BundleModel.remove_one_to_decrement_up(bundle_id)
            BundleModel.remove_has_voted('down', bundle_id, current_user.id)
            BundleModel.has_voted('up', bundle_id, current_user.id)

            _ = AccountModel.update_like_gamification(profil_game_user.id, "add_one_to_like")
            _ = AccountModel.update_like_gamification(profil_game_user.id, "remove_one_to_dislike")

    elif vote_type == 'down':
        if not already_vote:
            BundleModel.decrement_up(bundle_id)
            BundleModel.has_voted('down', bundle_id, current_user.id)

            _ = AccountModel.update_like_gamification(profil_game_user.id, "add_one_to_dislike")
        elif already_vote_type == 'down':
            BundleModel.remove_one_to_decrement_up(bundle_id)
            BundleModel.remove_has_voted('down', bundle_id, current_user.id)

            _ = AccountModel.update_like_gamification(profil_game_user.id, "remove_one_to_dislike")
        elif already_vote_type == 'up':
            BundleModel.decrement_up(bundle_id)
            BundleModel.remove_one_to_increment_up(bundle_id)
            BundleModel.remove_has_voted('up', bundle_id, current_user.id)
            BundleModel.has_voted('down', bundle_id, current_user.id)

            _ = AccountModel.update_like_gamification(profil_game_user.id, "add_one_to_dislike")
            _ = AccountModel.update_like_gamification(profil_game_user.id, "remove_one_to_like")

    from app.core.db_class.db import BundleVote as _BV
    new_bv = _BV.query.filter_by(bundle_id=bundle_id, user_id=current_user.id).first()
    user_vote = new_bv.vote_type if new_bv else None

    return jsonify({
        "vote_up": bundle.vote_up,
        "vote_down": bundle.vote_down,
        "user_vote": user_vote
    }), 200


BUNDLE_VOTERS_PREVIEW_CAP = 50

@bundle_blueprint.route('/voters', methods=['GET'])
def bundle_voters():
    """List the users who voted up/down on a bundle (hover popover)."""
    bundle_id = request.args.get('bundleId', type=int)
    vote_type = request.args.get('voteType', type=str)
    if not bundle_id or vote_type not in ('up', 'down'):
        return jsonify({"message": "Invalid parameters"}), 400

    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return jsonify({"message": "Bundle not found"}), 404
    if not BundleModel.can_view_bundle(bundle):
        return jsonify({"message": "You don't have the permission to view this bundle"}), 401

    from app.core.db_class.db import BundleVote as _BV
    q = (_BV.query.filter_by(bundle_id=bundle_id, vote_type=vote_type)
         .order_by(_BV.created_at.desc()))
    total = q.count()
    users = [{
        'id':       v.user.id,
        'username': v.user.get_username(),
        'avatar':   v.user.get_avatar_url(),
    } for v in q.limit(BUNDLE_VOTERS_PREVIEW_CAP).all() if v.user]

    return jsonify({'users': users, 'total': total}), 200

#########################
#   Download section    #
#########################

def _release_download(bundle_id, part):
    """Frozen version of a per-section download (?release=<id|version>)."""
    from .bundle_release_core import release_zip, release_zip_part
    bundle, err = _release_guard(bundle_id)
    if err:
        return err
    rel, err = _requested_release(bundle_id)
    if err:
        return err
    BundleModel.increment_download_count(bundle_id)
    safe_name = "".join(c for c in bundle.name if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_') or "bundle"
    safe_ver = "".join(c for c in rel.version if c.isalnum() or c in ".-_+")
    buf = release_zip(rel) if part == "full" else release_zip_part(rel, part)
    suffix = {"full": "", "structure": "_structure", "rules": "_rules", "files": "_files"}[part]
    return send_file(buf, as_attachment=True, download_name=f"{safe_name}_{safe_ver}{suffix}.zip", mimetype='application/zip')


@bundle_blueprint.route('/download', methods=['GET'])
def download_bundle():
    bundle_id = request.args.get("bundle_id", type=int)
    if request.args.get("release"):
        return _release_download(bundle_id, "rules")
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    rules = BundleModel.get_rules_from_bundle(bundle_id)  

    if not rules or not bundle:
        return {
            "success": False,
            "message": "No rules on this bundle to download",
            "toast_class": "danger"
        }, 400
    
    if not BundleModel.can_view_bundle(bundle):
        return {
            "success": False,
            "message": "You don't have the permission to download this bundle",
            "toast_class": "danger"
        }, 401

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        bundle_info_json = json.dumps(bundle.to_json(), indent=2)
        zip_file.writestr("bundle_info.txt", bundle_info_json)

        for rule in rules:
            ext = rule.get_extension()
            base_filename = f"{_safe_zip_name((rule.title or '').replace(' ', '_').rstrip('.'), 'rule')}_{rule.id}"

            code_filename = f"{base_filename}.{ext}"
            zip_file.writestr(code_filename, rule.to_string or "")

            json_filename = f"{base_filename}.json"
            rule_json = json.dumps(rule.to_json(), indent=2)
            zip_file.writestr(json_filename, rule_json)

    # add 1 to download count
    BundleModel.increment_download_count(bundle_id)

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=f"{bundle.name}.zip",
        mimetype='application/zip'
    ), 200



def _safe_zip_name(name, fallback="untitled"):
    """One path segment for a ZIP entry built from a user-typed name.
    Strips separators and control chars and refuses '.'/'..', so an archive
    can never write outside its extraction folder (zip slip)."""
    clean = "".join(c for c in str(name or "") if c.isprintable())
    clean = clean.replace("/", "_").replace("\\", "_").replace(":", "_").strip()
    if clean in ("", ".", ".."):
        return fallback
    return clean[:200]


def add_node_to_zip(zip_file, node, current_path=""):
    """
    Independent recursive function to build the ZIP directory tree.
    """
    if node.rule_id and (not node.rule or node.rule.is_deleted):
        return  # trashed / missing rule — never ship its content
    if node.rule_id and node.rule:
        filename = f"{_safe_zip_name((node.rule.title or '').rstrip('.'), 'rule')}.{node.rule.get_extension()}"
        content = node.rule.to_string
    else:
        filename = _safe_zip_name(node.name)
        content = node.custom_content or ""

    entry_path = f"{current_path}/{filename}".strip("/")

    if node.node_type == 'folder':
        if not node.children:
            zip_file.writestr(f"{entry_path}/", "")
        
        for child in node.children:
            add_node_to_zip(zip_file, child, entry_path)
    else:
        zip_file.writestr(entry_path, content)


@bundle_blueprint.route('/download_structure', methods=['GET'])
def download_bundle_structure():     
    bundle_id = request.args.get("bundle_id", type=int)
    if request.args.get("release"):
        return _release_download(bundle_id, "structure")
    bundle = BundleModel.get_bundle_by_id(bundle_id)

    if not bundle:
        return {
            "success": False,
            "message": "Bundle not found",
            "toast_class": "danger"
        }, 400

    # Permission check
    if not BundleModel.can_view_bundle(bundle):
        return {
            "success": False,
            "message": "Unauthorized access",
            "toast_class": "danger"
        }, 401

    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        bundle_metadata = bundle.to_json()
        zip_file.writestr("bundle_metadata.json", json.dumps(bundle_metadata, indent=4))

        root_nodes = BundleModel.get_only_root_nodes(bundle_id)
        for root in root_nodes:
            add_node_to_zip(zip_file, root)

    zip_buffer.seek(0)
    
    safe_bundle_name = "".join([c for c in bundle.name if c.isalnum() or c in (' ', '_')]).strip().replace(' ', '_')
    
    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=f"{safe_bundle_name}_structure.zip",
        mimetype='application/zip'
    )

def _add_custom_files_to_zip(zip_file, node, current_path=""):
    """Like add_node_to_zip, but only writes the non-rule files (README.md,
    notes.txt…), keeping their folder path. Empty folders are skipped."""
    entry_path = f"{current_path}/{_safe_zip_name(node.name)}".strip("/")
    if node.node_type == 'folder':
        for child in node.children:
            _add_custom_files_to_zip(zip_file, child, entry_path)
        return 0
    if node.rule_id:
        return 0
    zip_file.writestr(entry_path, node.custom_content or "")
    return 1


def _count_custom_files(node):
    if node.node_type == 'folder':
        return sum(_count_custom_files(c) for c in node.children)
    return 0 if node.rule_id else 1


@bundle_blueprint.route('/download_files', methods=['GET'])
def download_bundle_files():
    """ZIP of every non-rule file in the bundle structure, folder layout kept."""
    bundle_id = request.args.get("bundle_id", type=int)
    if bundle_id and request.args.get("release"):
        return _release_download(bundle_id, "files")
    bundle = BundleModel.get_bundle_by_id(bundle_id) if bundle_id else None
    if not bundle:
        return {"success": False, "message": "Bundle not found", "toast_class": "danger"}, 404

    if not BundleModel.can_view_bundle(bundle):
        return {"success": False, "message": "Unauthorized access", "toast_class": "danger"}, 401

    root_nodes = BundleModel.get_only_root_nodes(bundle_id)
    if not sum(_count_custom_files(r) for r in root_nodes):
        return {"success": False, "message": "This bundle has no files besides rules", "toast_class": "warning-subtle"}, 404

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root in root_nodes:
            _add_custom_files_to_zip(zip_file, root)
    zip_buffer.seek(0)

    safe_bundle_name = "".join([c for c in bundle.name if c.isalnum() or c in (' ', '_')]).strip().replace(' ', '_')
    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=f"{safe_bundle_name}_files.zip",
        mimetype='application/zip'
    )

def _full_bundle_readme(bundle, meta, tags, vulns, rules, n_files):
    """README.md at the root of the full export: everything a human needs
    to understand the bundle without opening Rulezet."""
    def md_cell(v):
        return str(v).replace("|", "\\|").replace("\n", " ")

    lines = [f"# {bundle.name}", ""]
    lines += [
        "| | |", "|---|---|",
        f"| **UUID** | `{bundle.uuid}` |",
        f"| **Author** | {md_cell(meta.get('user_name') or meta.get('author') or '—')} |",
        f"| **Created** | {meta.get('created_at', '—')} |",
        f"| **Updated** | {meta.get('updated_at', '—')} |",
        f"| **Visibility** | {'Public' if bundle.access else 'Private'} |",
        f"| **Verified** | {'Yes' if bundle.is_verified else 'No'} |",
        f"| **Rules** | {len(rules)} |",
        f"| **Files & documents** | {n_files} |",
        f"| **Formats** | {md_cell(', '.join(sorted({(r.format or 'unknown').lower() for r in rules})) or '—')} |",
        f"| **Votes** | 👍 {bundle.vote_up or 0} · 👎 {bundle.vote_down or 0} |",
        "",
        "## Description", "",
        (bundle.description or "_No description._").strip(), "",
        "## Tags", "",
    ]
    lines += [f"- `{t.get('name')}`" + (f" — {md_cell(t.get('description'))}" if t.get('description') else "") for t in tags] or ["_None_"]
    lines += ["", "## Vulnerabilities (CVE / identifiers)", ""]
    lines += [f"- {v}" for v in vulns] or ["_None_"]
    lines += ["", "## Rules", "", "| Title | Format | UUID |", "|---|---|---|"]
    lines += [f"| {md_cell(r.title)} | {r.format or '—'} | `{r.uuid}` |" for r in rules] or ["| — | — | — |"]
    lines += [
        "", "## Archive layout", "",
        "- `README.md` — this file",
        "- `description.md` — the bundle description (Markdown)",
        "- `bundle.json` — full metadata: bundle, tags, vulnerabilities, rules, structure tree",
        "- `structure/` — the bundle's folders, rules and files exactly as organised on Rulezet",
        "- `rules/` — every rule with its full JSON metadata",
        "- `attack_coverage.json` — MITRE ATT&CK coverage",
        "- `misp_event.json` — the bundle as a MISP event",
        "",
        "---",
        "> ⚠️ Community content: rules and files are user-submitted and not reviewed by Rulezet. "
        "Inspect them before running or deploying, preferably in an isolated environment.",
        "",
    ]
    return "\n".join(lines)


@bundle_blueprint.route('/download_full', methods=['GET'])
def download_bundle_full():
    """Everything about a bundle in one ZIP: README + description, metadata
    (tags, CVEs, rules), the full structure with rules and files, per-rule
    JSON, ATT&CK coverage and the MISP event."""
    bundle_id = request.args.get("bundle_id", type=int)
    if bundle_id and request.args.get("release"):
        return _release_download(bundle_id, "full")
    bundle = BundleModel.get_bundle_by_id(bundle_id) if bundle_id else None
    if not bundle:
        return {"success": False, "message": "Bundle not found", "toast_class": "danger"}, 404

    if not BundleModel.can_view_bundle(bundle):
        return {"success": False, "message": "Unauthorized access", "toast_class": "danger"}, 401

    meta = bundle.to_json()
    meta.pop("view_count", None)
    tags = BundleModel.get_tags_for_bundle_json(bundle_id)
    vulns = BundleModel.get_vulnerabilities_for_bundle(bundle_id)
    rules = BundleModel.get_rules_from_bundle(bundle_id)
    root_nodes = BundleModel.get_only_root_nodes(bundle_id)
    n_files = sum(_count_custom_files(r) for r in root_nodes)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.md", _full_bundle_readme(bundle, meta, tags, vulns, rules, n_files))
        zf.writestr("description.md", bundle.description or "")

        zf.writestr("bundle.json", json.dumps({
            "bundle": meta,
            "tags": tags,
            "vulnerabilities": vulns,
            "rules": [{"id": r.id, "uuid": r.uuid, "title": r.title, "format": r.format} for r in rules],
            "structure": [n.to_tree_json() for n in root_nodes],
        }, indent=2, default=str))

        for root in root_nodes:
            add_node_to_zip(zf, root, "structure")

        for rule in rules:
            base = f"rules/{_safe_zip_name((rule.title or '').replace(' ', '_').rstrip('.'), 'rule')}_{rule.id}"
            zf.writestr(f"{base}.{rule.get_extension()}", rule.to_string or "")
            zf.writestr(f"{base}.json", json.dumps(rule.to_json(), indent=2, default=str))

        # Optional extras — a failure there must not cost the user the whole export
        try:
            zf.writestr("attack_coverage.json", json.dumps(BundleModel.get_attack_coverage(bundle_id), indent=2, default=str))
        except Exception:
            pass
        try:
            event = get_bundle_misp_event(bundle_id)
            if event:
                zf.writestr("misp_event.json", json.dumps(event, indent=2, default=str))
        except Exception:
            pass

    BundleModel.increment_download_count(bundle_id)
    zip_buffer.seek(0)
    safe_bundle_name = "".join([c for c in bundle.name if c.isalnum() or c in (' ', '_')]).strip().replace(' ', '_') or "bundle"
    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=f"{safe_bundle_name}_full.zip",
        mimetype='application/zip'
    )

@bundle_blueprint.route('/download_misp', methods=['GET'])
def download_bundle_misp():
    bundle_id = request.args.get("bundle_id", type=int)
    if not bundle_id:
        return {"success": False, "message": "Missing bundle_id", "toast_class": "danger-subtle"}, 400

    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {"success": False, "message": "Bundle not found", "toast_class": "danger-subtle"}, 400

    if not BundleModel.can_view_bundle(bundle):
        return {"success": False, "message": "Unauthorized access", "toast_class": "danger"}, 401

    event_json = get_bundle_misp_event(bundle_id)
    if not event_json:
        return {"success": False, "message": "Failed to generate MISP event", "toast_class": "danger-subtle"}, 500

    safe_name = "".join([c for c in bundle.name if c.isalnum() or c in (' ', '_')]).strip().replace(' ', '_')

    # # return a json 
    # json_= json.dumps(event_json, indent=4)

    # # return the content too 
    # return {
    #     "message": "MISP event generated successfully",
    #     "event":  json_,
    #     "success": True,
    #     "toast_class": "success-subtle"
    # }, 200
    return send_file(
        io.BytesIO(json.dumps(event_json, indent=4).encode('utf-8')),
        as_attachment=True,
        download_name=f"{safe_name}_misp_event.json",
        mimetype='application/json'
    )
################################
#   Rule part of the bundle    #
################################

@bundle_blueprint.route("/get_bundle_list_rule_part_of", methods=['GET'])
def get_bundle_list_rule_part_of() :     
    """get all bundles where the rule is part of"""     
    rule_id = request.args.get('rule_id',  type=int)
    if not rule_id:
        return {"message": "No rule id provided"}, 400

    bundles = BundleModel.get_bundles_by_rule(rule_id)
    if bundles:
        return {"bundles": [b.to_json() for b in bundles]}, 200

    return {"message": "No bundles found for this rule"}, 200


###############################
#   Bundle by user section    #
###############################

@bundle_blueprint.route("/get_bundles_page_filter_with_id", methods=['GET'])
def get_bundles_page_filter_with_id():     
    """get all the bundles of a user for pages"""     
    user_id = request.args.get('user_id', type=int)
    page = request.args.get('page', 1, type=int)
    search = request.args.get("searchBundle", None)
    sort_by = request.args.get("sortByBundle", "newest")
    rule_type = request.args.get("ruleTypeBundle", "")

    if not user_id:
        return {"message": "No user id provided"}, 400

    bundles = BundleModel.get_bundles_of_user_with_id_page(user_id, page, search,sort_by, rule_type)
    
    if bundles.total > 0:
        return {
            "bundles_list": [r.to_json() for r in bundles.items],
            "total_pages": bundles.pages,
            "total_bundles": bundles.total
        }, 200

    return {"message": "No Bundle"}, 200



#############
#   Update  #
#############

# Transforme from BundleRuleAssociation to a structure compatible with the UI
@bundle_blueprint.route("/update_bundle_from_structure", methods=['POST'])  # state-changing: POST + CSRF (was GET)
@login_required
def update_bundle_from_structure():
    bundle_id = request.args.get("id", type=int)
    if not bundle_id:
        return {"message": "No bundle id provided", "toast_class": "danger-subtle"}, 400
    if not current_user.is_admin():
        return {"message": "You don't have the permission to do that !", "toast_class": "danger-subtle"}, 401
   # take all the rule associate to ths bundle and create a structure with BundleNode (create one folder and put all the rule id in there)
    success, msg = BundleModel.update_bundle_from_rule_id_into_structure(bundle_id)

    if not success:
        return {"message": msg, "toast_class": "danger-subtle"}, 500

    return {"toast_class": "success-subtle", "message": "Bundle updated successfully"}, 200



#######################
#   Comment section   #
#######################

@bundle_blueprint.route("/add_comment", methods=['POST'])  # state-changing: POST + CSRF (was GET)
def add_comment():
    """Add a comment to a bundle."""

    if not current_user.is_authenticated:
        return {"message": "You must be logged in to add a comment", "toast_class": "warning-subtle"}, 401

    bundle_id = request.args.get('bundle_id', type=int)
    content = request.args.get('content', type=str)
    parent_comment_id = request.args.get('parent_comment_id', type=int, default=None)

    if not bundle_id or not content:
        return {"message": "Missing bundle_id or content", "toast_class": "danger-subtle"}, 400

    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {"message": "Bundle not found", "toast_class": "danger-subtle"}, 404

    message, success = BundleModel.add_comment_to_bundle(bundle_id, current_user, content, parent_comment_id)
    if success:
        from app.core.db_class.db import CommentBundle
        new_c = CommentBundle.query.filter_by(bundle_id=bundle_id, user_id=current_user.id).order_by(CommentBundle.id.desc()).first()
        if new_c:
            log_activity("comment.add", f"Added comment on bundle id={bundle_id}",
                         target_type="bundle_comment", target_id=new_c.id,
                         extra={"bundle_id": bundle_id, "bundle_uuid": bundle.uuid},
                         is_public=bool(bundle.access))
        return {"message": message, "toast_class": "success-subtle"}, 200
    else:
        return {"message": message, "toast_class": "danger-subtle"}, 500


@bundle_blueprint.route("/get_comments", methods=['GET'])
def get_comments():
    """Get all comments for a bundle. (parents and children and pagginated)"""
    bundle_id = request.args.get('bundle_id', None)
    page = request.args.get('page', 1, type=int)
    if not bundle_id:
        return {"message": "Missing bundle_id", "toast_class": "danger-subtle"}, 400

    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {"message": "Bundle not found", "toast_class": "danger-subtle"}, 404
    if not BundleModel.can_view_bundle(bundle):          # was readable for private bundles
        return {"message": "Access denied", "toast_class": "danger-subtle"}, 403

    comments = BundleModel.get_comments_for_bundle(bundle_id, page)

    return {
        "comments": [c.to_json() for c in comments.items],
        "total_pages": comments.pages,
        "total_comments": comments.total
    }, 200

# delete_comment

@bundle_blueprint.route("/delete_comment", methods=['POST'])  # state-changing: POST + CSRF (was GET)
@login_required
def delete_comment():
    comment_id = request.args.get('comment_id', type=int)

    if not comment_id:
        return {"message": "Missing comment_id", "toast_class": "danger-subtle"}, 400

    comment = BundleModel.get_comment_bundle_by_id(comment_id)
    if not comment:
        return {"message": "Comment not found", "toast_class": "danger-subtle"}, 404

    if comment.user_id != current_user.id and not current_user.is_admin():
        return {"message": "You don't have the permission to do that !", "toast_class": "danger-subtle"}, 401


    bundle_id  = comment.bundle_id
    bundle_obj = BundleModel.get_bundle_by_id(bundle_id)
    success = BundleModel.delete_comment_bundle(comment_id)
    if success:
        log_activity("comment.delete", f"Deleted bundle comment id={comment_id}",
                     target_type="bundle_comment", target_id=comment_id,
                     extra={"bundle_id": bundle_id,
                            "bundle_uuid": bundle_obj.uuid if bundle_obj else None})
        return {"message": "Comment deleted.", "toast_class": "success-subtle"}, 200
    else:
        return {"message": "Not authorized or comment not found.", "toast_class": "danger-subtle"}, 403
    
# edit_comment

@bundle_blueprint.route("/edit_comment", methods=['POST'])  # state-changing: POST + CSRF (was GET)
@login_required
def edit_comment():
    comment_id = request.args.get('comment_id', type=int)
    content = request.args.get('content', type=str)

    if not comment_id or not content:
        return {"message": "Missing comment_id or content", "toast_class": "danger-subtle"}, 400

    comment = BundleModel.get_comment_bundle_by_id(comment_id)
    if not comment:
        return {"message": "Comment not found", "toast_class": "danger-subtle"}, 404

    if comment.user_id != current_user.id and not current_user.is_admin():
        return {"message": "You don't have the permission to do that !", "toast_class": "danger-subtle"}, 401

    success = BundleModel.edit_comment_bundle(comment_id, content)
    if success:
        return {"message": "Comment edited.", "toast_class": "success-subtle"}, 200
    else:
        return {"message": "Not authorized or comment not found.", "toast_class": "danger-subtle"}, 403
    
@bundle_blueprint.route("/add_reaction", methods=['POST'])  # state-changing: POST + CSRF (was GET)
@login_required
def add_reaction():
    """ Add a reaction to a comment."""
    comment_id = request.args.get('comment_id', type=int)
    reaction_type = request.args.get('reaction_type', type=str)
    bundle_id = request.args.get('bundle_id', type=int)

    if not comment_id or not reaction_type:
        return {"message": "Missing comment_id or reaction_type", "toast_class": "danger-subtle"}, 400

    comment = BundleModel.get_comment_bundle_by_id(comment_id)
    if not comment:
        return {"message": "Comment not found", "toast_class": "danger-subtle"}, 404

    success, message = BundleModel.add_reaction_to_comment(comment_id, current_user.id, reaction_type, bundle_id)
    if success:
        return {"message": message, "toast_class": "success-subtle"}, 200
    else:
        return {"message": message, "toast_class": "danger-subtle"}, 500
    


@bundle_blueprint.route('/get_bundle_tag_ids/<int:bundle_id>')
@login_required
def get_bundle_tag_ids(bundle_id):
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle or not BundleModel.can_view_bundle(bundle):
        return jsonify({"success": False, "message": "Access denied"}), 403
    tag_ids = BundleModel.get_tag_ids_for_bundle(bundle_id)
    return jsonify({"success": True, "tag_ids": tag_ids})


@bundle_blueprint.route('/get_bundle_tags_display/<int:bundle_id>')
def get_bundle_tags_display(bundle_id):
    """Returns full tag objects associated with a bundle for display purposes."""
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle or not BundleModel.can_view_bundle(bundle):
        return jsonify({"success": False, "message": "Access denied"}), 403
    try:
        tags = BundleModel.get_tags_for_bundle(bundle_id)
        
        return jsonify({
            "success": True, 
            "tags": [t.to_json() for t in tags],
            "total_tags": len(tags)

        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
@bundle_blueprint.route('/get_bundle_vulnerabilities_display/<int:bundle_id>')
def get_bundle_vulnerabilities_display(bundle_id):
    """Returns the list of vulnerability identifier strings."""
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle or not BundleModel.can_view_bundle(bundle):
        return jsonify({"success": False, "message": "Access denied"}), 403
    try:
        v_list = BundleModel.get_vulnerabilities_for_bundle(bundle_id)
        
        return jsonify({
            "success": True, 
            "vulnerabilities": v_list, 
            "total_vulnerabilities": len(v_list)
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@bundle_blueprint.route('/get_all_tags_usage')
def get_all_tags_usage():
    try:
        tags = BundleModel.get_all_used_tags_with_counts()
        return jsonify({
            "success": True,
            "tags": tags
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
@bundle_blueprint.route('/get_all_vulnerabilities_usage')
def get_all_vulnerabilities_usage():
    try:
        vulnerabilities = BundleModel.get_all_vulnerabilities_with_counts()
        return jsonify({
            "success": True,
            "vulnerabilities": vulnerabilities
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
@bundle_blueprint.route('/get_bundle_creators_usage')
def get_bundle_creators_usage():
    from app.core.db_class.db import Bundle, User
    from sqlalchemy import func
    from app import db
    results = (db.session.query(User.first_name, func.count(Bundle.id).label('cnt'))
               .join(Bundle, Bundle.user_id == User.id)
               .group_by(User.id, User.first_name)
               .order_by(func.count(Bundle.id).desc())
               .all())
    return jsonify([{'name': r.first_name, 'count': r.cnt} for r in results if r.first_name])


@bundle_blueprint.route("/get_tags/<int:bundle_id>")
def get_bundle_tags(bundle_id):
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle or not BundleModel.can_view_bundle(bundle):
        return jsonify({"tags": [], "message": "Access denied"}), 403
    try:
        user_id = request.args.get('user_id', type=int)

        tags_data = BundleModel.get_tags_for_bundle_json(bundle_id, user_id)
        
        return jsonify({"tags": tags_data}), 200
    except Exception as e:
        return jsonify({"tags": [], "error": str(e)}), 500
    

@bundle_blueprint.route('/vulnerabilities/<string:target_type>/<int:target_id>')
@login_required
def get_vulnerabilities(target_type, target_id):
    if target_type == 'bundle':
        item = BundleModel.get_bundle_by_id(target_id)
    else:
        return jsonify({"message": "Invalid target type", "vulnerability_identifiers": []}), 400
        
    return jsonify(item.to_json().get('vulnerability_identifiers', []))



@bundle_blueprint.route('/my-bundles')
@login_required
def my_bundles():
    bundles = BundleModel.get_bundles_by_user_id(current_user.id)
    
    bundle_data = []
    for b in bundles:
        root_nodes = BundleModel.get_only_root_nodes(b.id)
        
        json_bundle = b.to_json()
        
        json_bundle['tree'] = [node.to_tree_json() for node in root_nodes]
        bundle_data.append(json_bundle)

    return jsonify({
        "success": True,
        "bundles": bundle_data,
        "total_bundles": len(bundle_data)
    })


@bundle_blueprint.route("/get_bundle_page", methods=['GET'])
def get_bundle_page():
    """Get a bundle and its associated rules with pagination."""
    bundle_id = request.args.get('bundle_id', type=int)
    page = request.args.get('page', type=int, default=1)
    
    if not bundle_id:
        return {"message": "Missing bundle_id parameter", "success": False}, 400

    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return {"message": f"No bundle found with id {bundle_id}", "success": False}, 404
    if not BundleModel.can_view_bundle(bundle):
        abort(403)

    pagination = BundleModel.get_paginated_rules_info_by_bundle(bundle_id, page)
    
    
    root_nodes = BundleModel.get_only_root_nodes(bundle_id)
    if not root_nodes:
        structure = [{"id": "root", "name": "Main Bundle", "type": "folder", "children": []}]
    else:
        structure = [node.to_tree_json() for node in root_nodes]

    bundle_data = bundle.to_json() if hasattr(bundle, 'to_json') else {}
    if current_user.is_authenticated:
        from app.core.db_class.db import BundleVote as _BV
        _bv = _BV.query.filter_by(bundle_id=bundle_id, user_id=current_user.id).first()
        bundle_data['user_vote'] = _bv.vote_type if _bv else None
    else:
        bundle_data['user_vote'] = None

    return {
        "success": True,
        "bundle": bundle_data,
        "rules": pagination.items,
        "pagination": {
            "current_page": pagination.page,
            "total_pages": pagination.pages,
            "total_rules": pagination.total,
            "has_next": pagination.has_next,
            "has_prev": pagination.has_prev
        },
        "structure": structure
    }, 200

@bundle_blueprint.route("/add-single-rule", methods=['POST'])
@login_required
def add_single_rule_to_bundle():
    data = request.get_json()
    if not data:
        return {"success": False, "message": "Missing JSON body", "toast_class": "danger-subtle"}, 400

    rule_id = data.get("rule_id")
    existing_bundle_id = data.get("existing_bundle_id")
    new_bundle_name = data.get("new_bundle_name", "").strip()
    new_bundle_description = data.get("new_bundle_description", "").strip()
    is_public = data.get("is_public", True)

    if not rule_id:
        return {"success": False, "message": "Missing rule_id", "toast_class": "danger-subtle"}, 400

    rule = RuleModel.get_rule(rule_id)
    if not rule:
        return {"success": False, "message": f"Rule {rule_id} not found", "toast_class": "danger-subtle"}, 404

    if not existing_bundle_id and not new_bundle_name:
        return {
            "success": False,
            "message": "Provide either an existing_bundle_id or a new_bundle_name",
            "toast_class": "danger-subtle"
        }, 400

    # This only resolves/creates the target bundle — it deliberately does NOT
    # add the rule to it. The user places it manually from the rule library
    # in the structure editor.
    if existing_bundle_id:
        bundle = BundleModel.get_bundle_by_id(existing_bundle_id)
        if not bundle:
            return {"success": False, "message": "Bundle not found", "toast_class": "danger-subtle"}, 404

        if bundle.user_id != current_user.id and not current_user.is_admin():
            return {"success": False, "message": "You don't have permission to edit this bundle", "toast_class": "danger-subtle"}, 403

        return {
            "success": True,
            "message": f"Bundle \"{bundle.name}\" ready",
            "toast_class": "success-subtle",
            "uuid": bundle.uuid,
            "id": bundle.id,
            "rule_ids": [rule_id]
        }, 200

    form_dict = {
        "name": new_bundle_name,
        "description": new_bundle_description,
        "public": is_public
    }
    new_bundle = BundleModel.create_bundle(form_dict, current_user)
    if not new_bundle:
        return {"success": False, "message": "Failed to create bundle", "toast_class": "danger-subtle"}, 500

    log_activity(
        "bundle.create",
        f"Created bundle '{new_bundle.name}'",
        target_type="bundle", target_id=new_bundle.id, target_uuid=new_bundle.uuid,
        extra={"bundle_name": new_bundle.name},
        is_public=True,
    )
    return {
        "success": True,
        "message": f"Bundle \"{new_bundle.name}\" created",
        "toast_class": "success-subtle",
        "uuid": new_bundle.uuid,
        "id": new_bundle.id,
        "rule_ids": [rule_id]
    }, 200


# ── BundleList component endpoint ──────────────────────────────────────────

@bundle_blueprint.route("/data_table", methods=['GET'])
def bundle_data_table():
    """Standardised paginated endpoint consumed by the BundleList Vue component."""
    from app.core.db_class.db import Bundle, Tag, BundleTagAssociation
    from sqlalchemy import asc, desc, or_

    page     = request.args.get('page',     1,    type=int)
    per_page = request.args.get('per_page', 12,   type=int)
    search   = (request.args.get('search',  '',   type=str) or '').strip()
    sort_by  = request.args.get('sort',     'created_at', type=str)
    sort_dir = request.args.get('dir',      'desc', type=str)
    user_id  = request.args.get('user_id',  None, type=int)
    tags_raw     = request.args.get('tags',         '',   type=str) or ''
    vulns_raw    = request.args.get('vulnerabilities', '', type=str) or ''
    creators_raw = request.args.get('creators',    '',   type=str) or ''
    attacks_raw  = request.args.get('attacks',     '',   type=str) or ''
    access       = request.args.get('access',      '',   type=str)  # 'public' | 'private' | ''

    ids_filter   = request.args.getlist('ids[]', type=int)

    tag_names    = [t.strip() for t in tags_raw.split(',')      if t.strip()]
    vuln_list    = [v.strip() for v in vulns_raw.split(',')     if v.strip()]
    creator_list = [c.strip() for c in creators_raw.split(',')  if c.strip()]
    attack_ids   = [a.strip().upper() for a in attacks_raw.split(',') if a.strip()]

    query = Bundle.query

    if ids_filter:
        query = query.filter(Bundle.id.in_(ids_filter))

    if search:
        like = f'%{search}%'
        query = query.filter(or_(Bundle.name.ilike(like), Bundle.description.ilike(like)))

    if tag_names:
        query = (query
                 .join(BundleTagAssociation, BundleTagAssociation.bundle_id == Bundle.id)
                 .join(Tag, Tag.id == BundleTagAssociation.tag_id)
                 .filter(Tag.name.in_(tag_names))
                 .distinct())

    if vuln_list:
        query = query.filter(or_(
            *[Bundle.vulnerability_identifiers.ilike(f'%"{v}"%') for v in vuln_list]
        ))

    if user_id:
        query = query.filter(Bundle.user_id == user_id)

    if creator_list:
        from app.core.db_class.db import User
        query = (query
                 .join(User, User.id == Bundle.user_id, isouter=False)
                 .filter(User.first_name.in_(creator_list)))

    if attack_ids:
        from app.core.db_class.db import BundleRuleAssociation, RuleAttackAssociation
        query = (query
                 .join(BundleRuleAssociation, BundleRuleAssociation.bundle_id == Bundle.id)
                 .join(RuleAttackAssociation, RuleAttackAssociation.rule_id == BundleRuleAssociation.rule_id)
                 .filter(RuleAttackAssociation.technique_id.in_(attack_ids))
                 .distinct())

    if access == 'public':
        query = query.filter(Bundle.access.is_(True))
    elif access == 'private':
        if current_user.is_authenticated:
            query = query.filter(Bundle.access.is_(False), Bundle.user_id == current_user.id)
        else:
            query = query.filter(False)
    else:
        if current_user.is_authenticated:
            if not current_user.is_admin():
                query = query.filter(or_(Bundle.access.is_(True), Bundle.user_id == current_user.id))
        else:
            query = query.filter(Bundle.access.is_(True))

    _sort_map = {
        'created_at':     Bundle.created_at,
        'updated_at':     Bundle.updated_at,
        'name':           Bundle.name,
        'vote_up':        Bundle.vote_up,
        'download_count': Bundle.download_count,
    }
    sort_col = _sort_map.get(sort_by, Bundle.created_at)
    query = query.order_by(desc(sort_col) if sort_dir == 'desc' else asc(sort_col))

    per_page = min(max(per_page, 1), 100)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for b in pagination.items:
        j = b.to_json()
        j.pop('view_count', None)
        j['tags'] = BundleModel.get_tags_for_bundle_json(b.id)
        items.append(j)

    # Same facts in card and table view: files/folders, latest release —
    # two grouped queries for the whole page (no per-bundle query).
    page_ids = [b.id for b in pagination.items]
    if page_ids:
        from sqlalchemy import func as _f, case as _case
        from app.core.db_class.db import BundleNode as _BN, BundleRelease as _BR
        counts = {bid: (files or 0, folders or 0) for bid, files, folders in (
            db.session.query(
                _BN.bundle_id,
                _f.sum(_case(((_BN.node_type == 'file') & (_BN.rule_id.is_(None)), 1), else_=0)),
                _f.sum(_case((_BN.node_type == 'folder', 1), else_=0)),
            ).filter(_BN.bundle_id.in_(page_ids)).group_by(_BN.bundle_id))}
        rel_rows = (db.session.query(_BR.bundle_id, _BR.version, _BR.created_at, _BR.id)
                    .filter(_BR.bundle_id.in_(page_ids))
                    .order_by(_BR.bundle_id, _BR.created_at.desc(), _BR.id.desc()).all())
        latest, n_rel = {}, {}
        for bid, version, created, _id in rel_rows:
            n_rel[bid] = n_rel.get(bid, 0) + 1
            latest.setdefault(bid, {"version": version, "created_at": created.strftime('%Y-%m-%d %H:%M')})
        for item in items:
            files, folders = counts.get(item['id'], (0, 0))
            item['number_of_files'] = int(files)
            item['number_of_folders'] = int(folders)
            item['latest_release'] = latest.get(item['id'])
            item['release_count'] = n_rel.get(item['id'], 0)

    try:
        from app.features.attack.attack_core import get_techniques_for_bundles_batch
        atk_map = get_techniques_for_bundles_batch([b.id for b in pagination.items])
        for item in items:
            item['attacks'] = atk_map.get(item['id'], [])
    except Exception:
        pass

    if current_user.is_authenticated:
        from app.core.db_class.db import BundleVote as _BV
        bundle_ids = [b.id for b in pagination.items]
        bv_rows = _BV.query.filter(
            _BV.bundle_id.in_(bundle_ids),
            _BV.user_id == current_user.id
        ).all()
        bv_map = {v.bundle_id: v.vote_type for v in bv_rows}
        for item in items:
            item['user_vote'] = bv_map.get(item['id'])
    else:
        for item in items:
            item['user_vote'] = None

    return jsonify({
        'items':       items,
        'total':       pagination.total,
        'total_pages': pagination.pages,
    })


@bundle_blueprint.route('/attacks_usage')
def bundle_attacks_usage():
    """Return techniques used in at least one bundle's rules (for the filter dropdown)."""
    from app import db
    from app.core.db_class.db import (
        BundleRuleAssociation, RuleAttackAssociation, AttackTechnique
    )
    from sqlalchemy import func

    rows = (
        db.session.query(
            RuleAttackAssociation.technique_id,
            func.count(RuleAttackAssociation.id).label('count'),
        )
        .join(BundleRuleAssociation, BundleRuleAssociation.rule_id == RuleAttackAssociation.rule_id)
        .group_by(RuleAttackAssociation.technique_id)
        .order_by(func.count(RuleAttackAssociation.id).desc())
        .all()
    )
    tech_ids = [r.technique_id for r in rows]

    techs = AttackTechnique.query.filter(AttackTechnique.technique_id.in_(tech_ids)).all()
    tech_map = {t.technique_id: t for t in techs}

    result = []
    for tid, cnt in [(r.technique_id, r.count) for r in rows]:
        tech = tech_map.get(tid)
        if not tech:
            continue
        result.append({
            'id':         tech.technique_id,
            'name':       tech.name,
            'tactic_keys': tech.tactic_keys or [],
            'count':      cnt,
        })

    return jsonify({'techniques': result})


@bundle_blueprint.route('/attack_coverage/<int:bundle_id>')
def attack_coverage(bundle_id):
    bundle = BundleModel.get_bundle_by_id(bundle_id)
    if not bundle:
        return jsonify({'error': 'Bundle not found'}), 404
    if not BundleModel.can_view_bundle(bundle):
        abort(403)
    rel, err = _requested_release(bundle_id)
    if err:
        return err
    data = BundleModel.get_attack_coverage(bundle_id, snapshot_rules=(rel.snapshot.get("rules") or {}) if rel else None)
    return jsonify(data)