from flask import Blueprint, flash, jsonify, render_template, request
from flask_login import current_user, login_required
import app.features.tags.tags_core as tags_core
import app.features.rule.rule_core as RuleModel
from app.core.utils.activity_log import log_activity


tags_blueprint = Blueprint(
    'tags',
    __name__,
    template_folder='templates',
    static_folder='static',
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _admin_only():
    # A Tag Manager (rule.tag_any) gets full management rights on this page —
    # same treatment as everywhere else that permission is checked.
    if not current_user.is_admin() and not current_user.has_permission('rule.tag_any'):
        return {"status": "error", "message": "Admin access required.",
                "toast_class": "danger-subtle"}, 403
    return None


def _can_edit_tag(tag_id):
    """Return error response if current user cannot edit this tag."""
    from app.core.db_class.db import Tag
    tag = Tag.query.get(tag_id)
    if not tag:
        return {"status": "error", "message": "Tag not found."}, 404
    if not current_user.is_admin() and tag.created_by != current_user.id:
        return {"status": "error", "message": "You can only edit your own tags.",
                "toast_class": "danger-subtle"}, 403
    return None


def _can_delete_tag(tag_id):
    """Return error response if current user cannot delete this tag."""
    from app.core.db_class.db import Tag
    tag = Tag.query.get(tag_id)
    if not tag:
        return {"status": "error", "message": "Tag not found."}, 404
    if not current_user.is_admin() and tag.created_by != current_user.id:
        return {"status": "error", "message": "You can only delete your own tags.",
                "toast_class": "danger-subtle"}, 403
    return None


# ─── Pages ───────────────────────────────────────────────────────────────────

@tags_blueprint.route('/admin/list', methods=['GET'])
@login_required
def list_tags():
    if not current_user.is_admin() and not current_user.has_permission('rule.tag_any'):
        flash('You need to be admin to access this page.', 'danger')
        return render_template("access_denied.html")
    return render_template('tags/list.html', tag_manager_view=not current_user.is_admin())


@tags_blueprint.route('/my_tags', methods=['GET'])
@login_required
def my_tags():
    return render_template("tags/my_tags.html")


# ─── Tag listing ─────────────────────────────────────────────────────────────

@tags_blueprint.route('/get_tags', methods=['GET'])
@login_required
def get_tags():
    err = _admin_only()
    if err: return err
    pagination = tags_core.get_tags(request.args)
    return {
        "status": "success",
        "tags": [t.to_json() for t in pagination.items],
        "total_pages": pagination.pages,
        "total_tags": pagination.total,
    }, 200


@tags_blueprint.route('/get_tags_bundle', methods=['GET'])
@login_required
def get_tags_bundle():
    pagination = tags_core.get_tags_bundle(request.args)
    return {
        "status": "success",
        "tags": [t.to_json() for t in pagination.items],
        "total_pages": pagination.pages,
        "total_tags": pagination.total,
    }, 200


@tags_blueprint.route('/get_all_tags', methods=['GET'])
@login_required
def get_all_tags():
    tags = tags_core.get_all_tags(request.args)
    return {"status": "success", "tags": [t.to_json() for t in tags], "total_tags": len(tags)}, 200


@tags_blueprint.route('/get_all_tags_by_type', methods=['GET'])
@login_required
def get_all_tags_by_type():
    tags = tags_core.get_all_tags_by_type(request.args)
    return {"status": "success", "tags": [t.to_json() for t in tags], "total_tags": len(tags)}, 200


@tags_blueprint.route('/get_my_tags', methods=['GET'])
@login_required
def get_my_tags():
    return jsonify([t.to_json() for t in tags_core.get_my_tags()])


@tags_blueprint.route('/get_my_tags_paged', methods=['GET'])
@login_required
def get_my_tags_paged():
    """Paginated personal tags (Manual source, owned by current user)."""
    pagination = tags_core.get_my_tags_paged(request.args)
    return {
        "status": "success",
        "tags": [t.to_json() for t in pagination.items],
        "total_tags": pagination.total,
        "total_pages": pagination.pages,
    }, 200


# ─── Family operations (admin only) ──────────────────────────────────────────

@tags_blueprint.route('/get_family', methods=['GET'])
@login_required
def get_family():
    err = _admin_only()
    if err: return err
    family = request.args.get('family')
    source = request.args.get('source')
    if not family:
        return {"status": "error", "message": "Family is required."}, 400
    tags = tags_core.get_tags_by_family(family, source)
    return {"status": "success", "tags": [t.to_json() for t in tags], "total": len(tags)}, 200


@tags_blueprint.route('/delete_family', methods=['POST'])
@login_required
def delete_family():
    err = _admin_only()
    if err: return err
    data = request.json or {}
    family = data.get('family')
    source = data.get('source')
    if not family:
        return {"status": "error", "message": "Family is required."}, 400
    deleted, msg = tags_core.remove_family(family, source)
    log_activity(
        "tag.family_delete",
        f"Deleted tag family '{family}' (source={source or 'all'}): {deleted} tag(s) removed",
        extra={"family": family, "source": source, "deleted_count": deleted},
        is_public=False,
    )
    return {"status": "success", "deleted": deleted, "message": msg, "toast_class": "success-subtle"}, 200


# ─── Single tag mutations ─────────────────────────────────────────────────────

@tags_blueprint.route('/remove_tag', methods=['GET'])
@login_required
def remove_tag():
    err = _admin_only()
    if err: return err
    tag_id = request.args.get("tag_id")
    success, message = tags_core.remove_tag(tag_id)
    cls = "success-subtle" if success else "danger-subtle"
    return {"status": "success" if success else "error", "message": message, "toast_class": cls}, (200 if success else 500)


@tags_blueprint.route('/remove_tags_bulk', methods=['POST'])
@login_required
def remove_tags_bulk():
    """Bulk delete tags. Admin: any tags. User: only their own Manual tags."""
    data = request.json or {}
    ids  = data.get('ids', [])
    if not isinstance(ids, list):
        return {"status": "error", "message": "ids must be a list."}, 400

    # non-admins: filter to only their own tags
    if not current_user.is_admin():
        from app.core.db_class.db import Tag
        owned = {t.id for t in Tag.query.filter(
            Tag.id.in_([int(i) for i in ids]),
            Tag.created_by == current_user.id,
            Tag.source == 'Manual',
        ).all()}
        ids = [i for i in ids if int(i) in owned]
        if not ids:
            return {"status": "error", "message": "No eligible tags to delete.", "toast_class": "warning-subtle"}, 400

    deleted, msg = tags_core.remove_tags_bulk(ids)
    if deleted > 0:
        log_activity(
            "tag.bulk_delete",
            f"Bulk deleted {deleted} tag(s) (ids={ids[:10]}{'...' if len(ids) > 10 else ''})",
            extra={"ids": ids, "deleted_count": deleted},
            is_public=False,
        )
        return {"status": "success", "deleted": deleted, "message": msg, "toast_class": "success-subtle"}, 200
    return {"status": "error", "deleted": 0, "message": msg, "toast_class": "danger-subtle"}, 500


@tags_blueprint.route('/toggle_visibility', methods=['GET'])
@login_required
def toggle_visibility():
    err = _admin_only()
    if err: return err
    tag_uuid = request.args.get("tag_uuid")
    if not tag_uuid:
        return {"status": "error", "message": "Tag UUID is required."}, 400
    success, message = tags_core.toggle_tag_visibility(tag_uuid)
    if success:
        log_activity("tag.toggle_visibility", f"Toggled visibility of tag uuid={tag_uuid}",
                     target_type="tag", target_uuid=tag_uuid)
    cls = "success-subtle" if success else "danger-subtle"
    return {"status": "success" if success else "error", "message": message, "toast_class": cls}, (200 if success else 500)


@tags_blueprint.route('/toggle_status', methods=['GET'])
@login_required
def toggle_status():
    err = _admin_only()
    if err: return err
    tag_uuid = request.args.get("tag_uuid")
    if not tag_uuid:
        return {"status": "error", "message": "Tag UUID is required."}, 400
    success, message = tags_core.toggle_tag_status(tag_uuid)
    if success:
        log_activity("tag.toggle_status", f"Toggled status of tag uuid={tag_uuid}",
                     target_type="tag", target_uuid=tag_uuid)
    cls = "success-subtle" if success else "danger-subtle"
    return {"status": "success" if success else "error", "message": message, "toast_class": cls}, (200 if success else 500)


@tags_blueprint.route('/edit_tag/<int:tag_id>', methods=['POST'])
@login_required
def edit_tag(tag_id):
    # admin: edit anything / user: only their own Manual tags
    err = _can_edit_tag(tag_id)
    if err: return err
    if not tag_id:
        return {"status": "error", "message": "Tag ID is required."}, 400
    success, message = tags_core.edit_tag(request.json, tag_id)
    if success:
        log_activity("tag.edit", f"Edited tag id={tag_id}",
                     target_type="tag", target_id=tag_id)
        return {"status": "success", "message": message, "toast_class": "success-subtle"}, 200
    if not message:
        return {"status": "error", "message": "Error while updating tag", "toast_class": "danger-subtle"}, 500
    return {"status": "error", "message": message, "toast_class": "warning-subtle"}, 201


@tags_blueprint.route('/create_tag', methods=['POST'])
@login_required
def create_tag():
    data = request.json
    if not data or not data.get('name'):
        return {"status": "error", "message": "Tag name is required."}, 400
    if 'visibility' not in data:
        data['visibility'] = 'private'
    tag = tags_core.create_tag(data, current_user)
    if tag is False:
        return {"status": "error", "message": "A tag with this name already exists.", "toast_class": "warning-subtle"}, 201
    if tag is None:
        return {"status": "error", "message": "Error while creating tag", "toast_class": "danger-subtle"}, 500
    log_activity("tag.create", f"Created tag '{tag.name}'",
                 target_type="tag", target_id=tag.id, target_uuid=tag.uuid)
    return {
        "status": "success",
        "message": "Tag created successfully!",
        "tag": {"id": tag.id, "uuid": tag.uuid, "name": tag.name, "color": tag.color},
        "toast_class": "success-subtle",
    }, 200


@tags_blueprint.route('/delete_tag/<int:tag_id>', methods=['POST'])
@login_required
def delete_tag(tag_id):
    # admin: delete anything / user: only their own tags
    err = _can_delete_tag(tag_id)
    if err: return err
    success, msg = tags_core.remove_tag(tag_id)
    if success:
        log_activity("tag.delete", f"Deleted tag id={tag_id}",
                     target_type="tag", target_id=tag_id)
    cls = "success-subtle" if success else "danger-subtle"
    return jsonify({"status": "success" if success else "error", "message": msg, "toast_class": cls}), (200 if success else 500)


# ─── MISP Taxonomies ─────────────────────────────────────────────────────────

@tags_blueprint.route('/get_tags_misp', methods=['GET'])
@login_required
def get_tags_misp():
    err = _admin_only()
    if err: return err
    result = tags_core.list_all_misp_taxonomies_meta(request.args)
    return {
        "status": "success",
        "tags": result["items"],
        "total_pages": result["pages"],
        "total_tags": result["total"],
        "page": result["page"],
    }, 200


@tags_blueprint.route('/add_tags_misp', methods=['GET'])
@login_required
def add_tag_misp():
    err = _admin_only()
    if err: return err
    uuid_param = request.args.get("uuid")
    if not uuid_param:
        return {"success": False, "message": "UUID is required.", "toast_class": "danger-subtle"}, 400
    success, message = tags_core.add_tags_from_misp_taxonomy(uuid_param, created_by=current_user)
    cls = "success-subtle" if success else "danger-subtle"
    return {"success": bool(success), "message": message, "toast_class": cls}, (200 if success else 500)


# ─── MISP Galaxies ───────────────────────────────────────────────────────────

@tags_blueprint.route("/get_tags_galaxy", methods=['GET'])
@login_required
def get_tags_galaxy():
    err = _admin_only()
    if err: return err
    result = tags_core.list_all_misp_galaxies_meta(request.args)
    return jsonify({
        "tags": result["items"],
        "total_tags": result["total"],
        "total_pages": result["pages"],
        "current_page": result["page"],
    })


@tags_blueprint.route("/get_galaxy_clusters/<uuid_param>", methods=['GET'])
@login_required
def get_galaxy_clusters(uuid_param):
    err = _admin_only()
    if err: return err
    result, error = tags_core.get_galaxy_clusters(uuid_param)
    if error:
        return jsonify({"message": error, "toast_class": "danger-subtle"}), 404
    return jsonify(result)


@tags_blueprint.route("/add_tags_galaxy", methods=['GET', 'POST'])
@login_required
def add_tags_galaxy():
    err = _admin_only()
    if err: return err
    if request.method == 'POST':
        data          = request.json or {}
        uuid_param    = data.get("uuid")
        cluster_uuids = data.get("cluster_uuids") or None
    else:
        uuid_param    = request.args.get("uuid")
        cluster_uuids = None
    success, message = tags_core.add_tags_from_misp_galaxy(uuid_param, current_user, cluster_uuids)
    cls = "success-subtle" if success else "danger-subtle"
    return jsonify({"message": message, "toast_class": cls}), (200 if success else 400)


@tags_blueprint.route('/admin/update_misp', methods=['POST'])
@login_required
def update_misp():
    """Launch a background job that git-pulls both MISP submodules then re-imports all taxonomies/galaxies."""
    err = _admin_only()
    if err: return err

    from app.features.jobs.jobs_core import create_job
    job = create_job(
        job_type   = 'update_misp_data',
        payload    = {},
        label      = 'Update MISP taxonomies & galaxies',
        created_by = current_user.id,
    )
    if not job:
        return jsonify({"success": False, "message": "Failed to create job", "toast_class": "danger-subtle"}), 500

    log_activity("admin.update_misp", "Launched MISP data update job",
                 target_type="job", target_id=job.id, target_uuid=job.uuid)
    return jsonify({"success": True, "job": job.to_json(), "message": "Update job queued!", "toast_class": "success-subtle"}), 200


@tags_blueprint.route('/admin/import_all_taxonomies', methods=['POST'])
@login_required
def import_all_taxonomies():
    """Launch a background job that imports every MISP taxonomy on disk, new ones included."""
    err = _admin_only()
    if err: return err

    from app.features.jobs.jobs_core import create_job
    job = create_job(
        job_type   = 'import_all_taxonomies',
        payload    = {},
        label      = 'Import all MISP taxonomies',
        created_by = current_user.id,
    )
    if not job:
        return jsonify({"success": False, "message": "Failed to create job", "toast_class": "danger-subtle"}), 500

    log_activity("admin.import_all_taxonomies", "Launched import-all-taxonomies job",
                 target_type="job", target_id=job.id, target_uuid=job.uuid)
    return jsonify({"success": True, "job": job.to_json(), "message": "Import job queued!", "toast_class": "success-subtle"}), 200


@tags_blueprint.route('/admin/import_all_galaxies', methods=['POST'])
@login_required
def import_all_galaxies():
    """Launch a background job that imports every MISP galaxy on disk, new ones included."""
    err = _admin_only()
    if err: return err

    from app.features.jobs.jobs_core import create_job
    job = create_job(
        job_type   = 'import_all_galaxies',
        payload    = {},
        label      = 'Import all MISP galaxies',
        created_by = current_user.id,
    )
    if not job:
        return jsonify({"success": False, "message": "Failed to create job", "toast_class": "danger-subtle"}), 500

    log_activity("admin.import_all_galaxies", "Launched import-all-galaxies job",
                 target_type="job", target_id=job.id, target_uuid=job.uuid)
    return jsonify({"success": True, "job": job.to_json(), "message": "Import job queued!", "toast_class": "success-subtle"}), 200


# ─── Rule validation (rulezet-validation false-positive gate) ────────────────

@tags_blueprint.route('/admin/validation', methods=['GET'])
@login_required
def validation():
    if not current_user.is_admin() and not current_user.has_permission('rule.tag_any'):
        flash('You need to be admin to access this page.', 'danger')
        return render_template("access_denied.html")
    return render_template('tags/validation.html', tag_manager_view=not current_user.is_admin())


@tags_blueprint.route('/admin/validation/launch', methods=['POST'])
@login_required
def launch_validation():
    """Launch a rulezet-validation run: sync this instance's rules, scan them
    against the known-clean baseline, quarantine anything that fires."""
    err = _admin_only()
    if err: return err

    data  = request.json or {}
    full  = bool(data.get('full', False))
    limit = data.get('limit')
    try:
        limit = int(limit) if limit else None
    except (TypeError, ValueError):
        limit = None

    from app.features.jobs.jobs_core import create_job
    job = create_job(
        job_type   = 'rule_validation_run',
        payload    = {'full': full, 'limit': limit},
        label      = 'Rule validation run' + (' (full)' if full else '') + (f' (limit={limit})' if limit else ''),
        created_by = current_user.id,
    )
    if not job:
        return jsonify({"success": False, "message": "Failed to create job", "toast_class": "danger-subtle"}), 500

    log_activity("admin.launch_validation", "Launched a rule validation run",
                 target_type="job", target_id=job.id, target_uuid=job.uuid)
    return jsonify({"success": True, "job": job.to_json(), "message": "Validation run queued!", "toast_class": "success-subtle"}), 200


_RISK_LEVELS = ("high", "medium", "low", "cannot-be-judged")

# The MISP taxonomy's own colors (#FF2B2B/#FFFF00/#33FF00/#FFC000) are the
# correct, official ones for the tag itself everywhere else it's shown — but
# as a solid badge/button fill in this review UI they read as neon rather
# than informative. This is a display-only override: the tag actually
# applied is still the real taxonomy tag (id/name untouched), only the
# swatch color shown here is muted.
_RISK_DISPLAY_COLORS = {
    "high":               "#C94A4A",
    "medium":             "#C99A2E",
    "low":                "#4C9A5B",
    "cannot-be-judged":   "#B8752E",
}

_RISK_LEVEL_BY_TAG_NAME = {f'false-positive:risk="{lvl}"': lvl for lvl in _RISK_LEVELS}


def _risk_tag_colors():
    """{level: {id, color}} for the 4 MISP 'false-positive' taxonomy 'risk'
    tags — resolved once per request rather than per rule."""
    from app.core.db_class.db import Tag
    rows = Tag.query.filter(Tag.name.in_([f'false-positive:risk="{lvl}"' for lvl in _RISK_LEVELS])).all()
    by_name = {t.name: t for t in rows}
    return {
        lvl: {"id": by_name[f'false-positive:risk="{lvl}"'].id, "color": _RISK_DISPLAY_COLORS[lvl]}
        for lvl in _RISK_LEVELS if f'false-positive:risk="{lvl}"' in by_name
    }


def _risk_level_from_tag(tag_string):
    """'false-positive:risk=high' -> 'high'. None if not that vocabulary."""
    if not tag_string or not tag_string.startswith("false-positive:risk="):
        return None
    return tag_string.split("=", 1)[1]


@tags_blueprint.route('/admin/validation/rules_data_table', methods=['GET'])
@login_required
def validation_rules_data_table():
    """RuleList-compatible data source for one validation run's quarantined
    rules — same shape as /rule/data_table, restricted to the ids that run
    quarantined, with each item's false-positive risk assessment embedded
    under `validation_risk` (opt-in RuleList extension, see ruleList.js's
    showValidationRisk prop)."""
    err = _admin_only()
    if err: return err

    from app.features.jobs.jobs_core import get_job_by_uuid
    job = get_job_by_uuid(request.args.get('job_uuid', ''))
    if not job or job.job_type != 'rule_validation_run':
        return jsonify({"items": [], "total": 0, "total_pages": 1}), 200

    entries = ((job.payload or {}).get('result') or {}).get('quarantined') or []
    by_rule_id = {e['rule_id']: e for e in entries if e.get('rule_id')}
    # A reviewer explicitly deciding "keep the current tag as-is" for a
    # mismatch (see /admin/validation/dismiss) — recorded per-run, not on
    # the rule itself, since a later run re-quarantining it deserves a
    # fresh look rather than inheriting an old dismissal forever.
    dismissed_rule_ids = set(((job.payload or {}).get('result') or {}).get('dismissed_rule_ids') or [])

    # "Resolved"/"mismatch" must be based on the rule's CURRENT tag, read
    # live right now — NOT upstream_tag (the rule's claim captured by
    # rulezet-validation's own sync step, from wherever it pulled rules:
    # INSTANCE_PUBLIC_URL, or rulezet.org when that's unset). On a dev box
    # that's routinely a different copy of the rule than the one sitting in
    # this local DB, so it can't be trusted to reflect "what the rule
    # actually has". A rule tagged low with 200 hits (proposed high) is a
    # disagreement worth flagging even if upstream_tag is stale or missing;
    # conversely a rule that already carried the right tag before anyone
    # reviewed it here is not a mismatch just because upstream said so.
    # Computed once for the WHOLE candidate set, before any filtering, so
    # the mismatch_only filter below uses the exact same definition as the
    # per-item badge shown later — not two different ideas of "mismatch".
    tags_by_rule_id = RuleModel.get_tags_for_rules_batch(list(by_rule_id.keys()))
    risk_by_rule_id = {}
    for rid, e in by_rule_id.items():
        proposed = _risk_level_from_tag(e.get('proposed_tag'))
        current_levels = {
            _RISK_LEVEL_BY_TAG_NAME[t.name]
            for t in tags_by_rule_id.get(rid, []) if t.name in _RISK_LEVEL_BY_TAG_NAME
        }
        risk_by_rule_id[rid] = {
            'proposed': proposed,
            'upstream': _risk_level_from_tag(e.get('upstream_tag')),
            'current_levels': current_levels,
            'mismatch': bool(current_levels) and proposed not in current_levels,
            'resolved': current_levels == ({proposed} if proposed else set()) or rid in dismissed_rule_ids,
        }

    # Dedicated risk filter — a fixed vocabulary of 4 levels (plus
    # "mismatch", the case the tool's own author flags as most worth
    # attention) that no real Rule column backs, so it's applied here by
    # narrowing the id set before it ever reaches get_rules_data_table().
    risk_level = (request.args.get('risk_level') or '').strip().lower()
    mismatch_only = request.args.get('mismatch_only', 'false').lower() == 'true'
    # Multi-select, like a tag picker — matches if a rule fired on ANY of
    # the chosen binaries (OR), same semantics as picking several tags.
    binaries = [b.strip().lower() for b in request.args.getlist('binary') if b.strip()]
    if risk_level or mismatch_only or binaries:
        by_rule_id = {
            rid: e for rid, e in by_rule_id.items()
            if (not risk_level or risk_by_rule_id[rid]['proposed'] == risk_level)
            # A dismissed rule can still be a live tag/proposed mismatch
            # (dismissing never changes the tag) but counts as resolved —
            # "Disagreements" must mean still-open ones, not ones a
            # reviewer already looked at and chose to keep as-is.
            and (not mismatch_only or (risk_by_rule_id[rid]['mismatch'] and not risk_by_rule_id[rid]['resolved']))
            and (not binaries or any(
                any(b in (m.get('file') or '').lower() for b in binaries)
                for m in (e.get('matched_files') or [])
            ))
        }

    if not by_rule_id:
        return jsonify({"items": [], "total": 0, "total_pages": 1}), 200

    search    = request.args.get('search', None, type=str)
    sort      = request.args.get('sort', None, type=str)
    direction = request.args.get('dir', 'asc', type=str)

    # get_rules_data_table() hard-caps per_page at 100 server-side no matter
    # what's asked for — loop it to collect every candidate (a validation run
    # flags at most a few hundred rules) instead of only ever seeing page 1.
    all_rules, _page = [], 1
    while True:
        pg = RuleModel.get_rules_data_table(
            page=_page, per_page=100, search=search, sort=sort, direction=direction,
            ids=list(by_rule_id.keys()),
        )
        all_rules.extend(pg.items)
        if _page >= pg.pages:
            break
        _page += 1

    colors = _risk_tag_colors()
    items = RuleModel.serialize_rules_for_data_table(all_rules, current_user)
    for d in items:
        e = by_rule_id.get(d['id'], {})
        risk = risk_by_rule_id[d['id']]
        # Same muted override as the risk badge/chart/quick-pick, applied to
        # the rule's actual tag chips too (shown via TagsDisplaysList in the
        # Tags column) — otherwise "medium" reads as one color in the risk
        # badge and the taxonomy's own neon yellow right next to it.
        for t in d.get('tags') or []:
            level = _RISK_LEVEL_BY_TAG_NAME.get(t.get('name'))
            if level:
                t['color'] = _RISK_DISPLAY_COLORS[level]
        d['validation_risk'] = {
            "hits":            e.get('hits', 0),
            "proposed_level":  risk['proposed'],
            "proposed_tag_id": colors.get(risk['proposed'], {}).get('id'),
            "proposed_color":  colors.get(risk['proposed'], {}).get('color'),
            "upstream_level":  risk['upstream'],
            "upstream_color":  colors.get(risk['upstream'], {}).get('color'),
            "mismatch":        risk['mismatch'],
            "matched_files":   e.get('matched_files') or [],
            "resolved":        risk['resolved'],
            "dismissed":       d['id'] in dismissed_rule_ids,
        }

    # Counted before any pending_only truncation below — RuleList's own
    # "select all N pages" banner uses this instead of the plain total so it
    # never offers to sweep up rows that have no checkbox to begin with.
    pending_total = sum(1 for d in items if not d['validation_risk']['resolved'])

    # "Hide already-tagged" — an explicit opt-out for reviewers who don't
    # want a screen full of checkmarks once most of a run is done. Mutually
    # exclusive with resolved_only (the report's "Reviewed" KPI tile) —
    # if a caller sends both, pending wins.
    if request.args.get('pending_only', 'false').lower() == 'true':
        items = [d for d in items if not d['validation_risk']['resolved']]
    elif request.args.get('resolved_only', 'false').lower() == 'true':
        items = [d for d in items if d['validation_risk']['resolved']]

    # Already-reviewed rules sink to the end (stable within each group —
    # the requested sort still applies inside "pending" and inside
    # "resolved") instead of being scattered wherever they happened to
    # land in the run's own order.
    items.sort(key=lambda d: d['validation_risk']['resolved'])

    requested_page     = request.args.get('page', 1, type=int)
    requested_per_page = request.args.get('per_page', 12, type=int)
    total      = len(items)
    start      = (requested_page - 1) * requested_per_page
    page_items = items[start:start + requested_per_page]
    total_pages = max(1, -(-total // requested_per_page)) if requested_per_page > 0 else 1

    return jsonify({
        "items":         page_items,
        "total":         total,
        "total_pages":   total_pages,
        "pending_total": pending_total,
    }), 200


@tags_blueprint.route('/admin/validation/dismiss', methods=['POST'])
@login_required
def validation_dismiss():
    """Mark quarantined rules reviewed WITHOUT changing their tag — the
    explicit "I looked at this mismatch and I'm keeping the current tag"
    call, as opposed to accept-proposed/apply-a-different-tag which both
    change something. Recorded on the RUN (payload.result.dismissed_rule_ids),
    not the rule, since a later run re-quarantining the same rule deserves a
    fresh look rather than inheriting an old dismissal forever."""
    err = _admin_only()
    if err: return err

    data = request.json or {}
    from app.features.jobs.jobs_core import get_job_by_uuid
    job = get_job_by_uuid(data.get('job_uuid', ''))
    if not job or job.job_type != 'rule_validation_run':
        return jsonify({"success": False, "message": "Validation run not found"}), 404

    try:
        rule_ids = {int(r) for r in (data.get('rule_ids') or [])}
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid rule ids"}), 400
    if not rule_ids:
        return jsonify({"success": False, "message": "No rule ids given"}), 400

    from app.core.db_class.db import db

    p = dict(job.payload or {})
    result = dict(p.get('result') or {})
    dismissed = set(result.get('dismissed_rule_ids') or [])
    dismissed.update(rule_ids)
    result['dismissed_rule_ids'] = list(dismissed)
    p['result'] = result
    job.payload = p
    db.session.commit()

    return jsonify({"success": True, "dismissed": len(rule_ids)}), 200


@tags_blueprint.route('/admin/validation/baseline_files', methods=['GET'])
@login_required
def validation_baseline_files():
    """The known-clean binaries a validation run is actually measured
    against — collect_baseline() is deterministic given the same settings,
    so this reproduces the exact kept/excluded split a real run used
    without needing to have recorded it anywhere. Skips hashing (digests={})
    since this is for display, not for reproducing scans elsewhere."""
    err = _admin_only()
    if err: return err

    from rulezet_validation import config as rv_config, gate as rv_gate
    from app.features.jobs.job_handlers import RULE_VALIDATION_MIRROR_DIR

    settings = rv_config.load()
    settings['mirror_dir'] = str(RULE_VALIDATION_MIRROR_DIR)

    kept, excluded = rv_gate.collect_baseline(settings)
    manifest = rv_gate.baseline_manifest(kept, digests={})
    return jsonify({
        "count":          len(manifest),
        "files":          manifest,
        "dirs":           settings.get('baseline_dirs') or [],
        "excluded_files": sorted(f.name for f in excluded),
    }), 200