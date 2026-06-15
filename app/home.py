import json
import os
from flask import send_from_directory
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, send_from_directory, abort
from flask_login import current_user, login_required
from flask import get_flashed_messages
from flask_login import login_required, current_user

from app.core.utils.utils import get_version
from app.core.utils.activity_log import log_activity

from .features.rule import rule_core as RuleModel
from .features.account import account_core as AccountModel


home_blueprint = Blueprint(
    'home',
    __name__,
    template_folder='templates',
    static_folder='static'
)

#####################
#   Alert section   #
#####################

@home_blueprint.route("/request_to_check")
def inject_requests_to_validate() -> jsonify:
    """Get the number of  request to validate"""
    try:
        if current_user.is_admin():
            count = AccountModel.get_total_requests_to_check_admin()
        else:
            count = AccountModel.get_total_requests_to_check()
    except:
        count = 0
    return jsonify({"count": count})

###################
#   Home section  #
###################
@home_blueprint.route("/why_choose_rulezet")
def why():
    return render_template("why.html")

@home_blueprint.route("/")
def home() -> render_template:
    """Go to home page"""
    get_flashed_messages()
    show_import_hint = (
        current_user.is_authenticated
        and current_user.is_admin()
        and RuleModel.get_total_rules_count() == 0
    )
    return render_template("home.html", show_import_hint=show_import_hint)

@home_blueprint.route("/get_last_rules", methods=['GET'])
def get_last_rules() -> dict:
    """Get the last 10 rules create or update"""
    rules = RuleModel.get_last_rules_from_db()
    return {'rules': [r.to_json() for r in rules], 'success': True}, 200

@home_blueprint.route("/get_current_user_connected", methods=['GET'])
def get_current_user_connected() -> jsonify:
    """Is the current user an admin to vue JS"""
    if current_user.is_authenticated:
        return jsonify({"is_authenticated": True, "user_id": current_user.id})
    else:
        return jsonify({"is_authenticated": False})

######################
#   Request section  #
######################

@home_blueprint.route("/owner_request", methods=["POST", "GET"])
@login_required
def owner_request() -> redirect:
    """Get all the request to validate"""
    choice = request.args.get('choice', 1, type=int)
    if choice == 1:
        # one rule
        rule_id = request.args.get('rule_id')
        if not rule_id:
            return {"success": False, "message": "No rule with this id!" , "toast_class" : "danger-subtle"}, 200
        rule = RuleModel.get_rule(rule_id)
        if current_user.id != rule.user_id:
            request_ = AccountModel.create_request(rule_id=rule_id, source="")
            if request_:
                return {"success": True, "message": "Ownership request submitted successfully !" , "toast_class" : "success-subtle"}, 200
        return {"success": False, "message": "You can create a request for your own rule !" , "toast_class" : "danger-subtle"}, 200
    elif choice == 2:
        # with source
        source = request.args.get('source')
        if not source:
            return {"success": False, "message": "No Source given !" , "toast_class" : "danger-subtle"}, 200
        rules = RuleModel.get_rule_by_source(source)
        if not rules:
            return {"success": False, "message": "No rule with this source!" , "toast_class" : "danger-subtle"}, 200
        AccountModel.create_request(rule_id=None, source=source)
        return {"success": True, "message": "Ownership request submitted successfully !" , "toast_class" : "success-subtle"}, 200
    else:
        return {"success": False, "message": "Error system" , "toast_class" : "danger-subtle"}, 500

    



@home_blueprint.route("/admin/request", methods=["POST", "GET"])
@login_required
def admin_requests() -> render_template:
    """Redirect to request section"""
    return render_template("admin/request.html")


@home_blueprint.route("/requests/<int:id>", methods=[ "GET"])
@login_required
def requests(id) -> render_template:
    """Redirect to request section"""
    return render_template("account/request_detail.html" , request_id=id)


@home_blueprint.route("/get_requests_page", methods=['GET'])
@login_required
def get_requests_page() -> json:
    """Get all the request in a page"""
    page = request.args.get('page', 1, type=int)
    if current_user.is_admin():
        requests_paginated = AccountModel.get_requests_page(page)
    else:
        requests_paginated = AccountModel.get_requests_page_user(page)
    total_requests = AccountModel.get_total_requests_to_check_admin()
    if requests_paginated.items:
        requests_list = []
        for r in requests_paginated.items:
            user = AccountModel.get_username_by_id(r.user_id)
            request_data = r.to_json()  
            
            request_data['user_name'] = user
            requests_list.append(request_data)
        return {
            "success": True,
            "pending_requests_list": requests_list,
            "pending_totalPages": requests_paginated.pages,  
        } , 200
    return {"message": "No requests found"}

@home_blueprint.route("/get_process_requests_page", methods=['GET'])
@login_required
def get_process_requests_page() -> json:
    """Get all the request in a page"""
    page = request.args.get('page', 1, type=int)
    if current_user.is_admin():
        requests_paginated = AccountModel.get_process_requests_page(page)
    else:
        requests_paginated = AccountModel.get_process_requests_page_user(page)

    if requests_paginated.items:
        requests_list = []
        for r in requests_paginated.items:
            user = AccountModel.get_username_by_id(r.user_id)
            request_data = r.to_json()  
            
            request_data['user_name'] = user
            requests_list.append(request_data)
        return {
            "success": True,
            "process_requests_list": requests_list,
            "process_totalPages": requests_paginated.pages,  
        } , 200
    return {"message": "No requests found"}


@home_blueprint.route("/get_request", methods=['GET'])
@login_required
def get_request() -> json:
    """Get the request """
    request_id = request.args.get('request_id', 1, type=int)
    request_ = AccountModel.get_request_by_id(request_id)
    if request_:
        if current_user.is_admin() or request_.user_id_to_send == current_user.id:
            return {
                "success": True,
                "current_request": request_.to_json() 
            } , 200
        else:
            return {
                "success": False,
                "current_request": None 
            } , 200
    return {"message": "No requests found"}

@home_blueprint.route("/get_concerned_rule", methods=['GET'])
@login_required
def get_concerned_rule() -> json:
    """Get all the get_concerned_rule in a page"""
    request_id = request.args.get('request_id', 1, type=int)
    page = request.args.get('page', 1, type=int)

    request_ = AccountModel.get_request_by_id(request_id)
    
    if current_user.is_admin():
        if request_.rule_source:
            concerned_rules_list = RuleModel.get_concerned_rules_admin_page(request_.rule_source, page , request_.user_id_to_send)
            nb_rules = RuleModel.get_concerned_rule_admin_count(request_.rule_source, page , request_.user_id_to_send)
        else:
            concerned_rules_list = []
            rule = RuleModel.get_rule(request_.rule_id)
            concerned_rules_list.append(rule)
            nb_rules = 1
    else:
        if request_.rule_source:
            concerned_rules_list = RuleModel.get_concerned_rules_page(request_.rule_source, page)
            nb_rules = RuleModel.get_concerned_rule_count(request_.rule_source)
        else:
            concerned_rules_list = []
            rule = RuleModel.get_rule(request_.rule_id)
            concerned_rules_list.append(rule)
            nb_rules = 1


    if concerned_rules_list:
        return {
            "success": True,
            "concerned_rules_list": [rule.to_json() for rule in concerned_rules_list],
            "Rules_totalPages": concerned_rules_list.pages if request_.rule_source else 1,
            "total_rules": nb_rules
        } , 200
    else:
        return {
            "success": False,
            "concerned_rules_list": [] 
        } , 200


@home_blueprint.route("/get_all_concerned_rules", methods=["GET"])
@login_required
def get_all_concerned_rules():
    request_id = request.args.get("request_id", type=int)

    if not request_id:
        return jsonify({"error": "Missing request_id"}), 400

    request_ = AccountModel.get_request_by_id(request_id)
    try:
        if current_user.is_admin():
            rules = RuleModel.get_concerned_rules_admin(request_.rule_source , request_.user_id_to_send)
            if len(rules) == 0:
                # not with source but only one rule
                rule_concerned = RuleModel.get_rule(request_.rule_id)
                rules.append(rule_concerned)
            result = [rule.to_json() for rule in rules]
            return jsonify({"all_concerned_rules": result})
        else:
            rules = RuleModel.get_concerned_rules(request_.rule_source)
            result = [rule.to_json() for rule in rules]
            return jsonify({"all_concerned_rules": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@home_blueprint.route("/get_made_requests_page", methods=["GET"])
@login_required
def get_made_requests_page() -> json:
    """Get all the requests made by the user in a page"""
    page = request.args.get('page', 1, type=int)
    requests_paginated = AccountModel.get_made_requests_page(page)
    if requests_paginated:
        return {
            "success": True,
            "made_requests_list": [request_.to_json() for request_ in requests_paginated],
            "made_totalPages": requests_paginated.pages,  
        } , 200
    return {"message": "No requests found"}, 200


@home_blueprint.route("/update_request", methods=["POST" ])
@login_required
def update_request_status() -> jsonify:
    """Update the request for vue JS"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Invalid or missing JSON"}), 400
    request_id = data.get('request_id')
    status = data.get('status')
    rule_ids = data.get('rule_list')

    rules = RuleModel.get_rules_by_ids(rule_ids)


    is_the_owner = AccountModel.is_the_owner(request_id)

    if current_user.is_admin() or is_the_owner:
        updated = AccountModel.update_request_status(request_id, status)
        if updated and status == "approved":
            log_activity("admin.request_approved",
                         f"Approved ownership request id={request_id} ({len(rules)} rules impacted)",
                         extra={"request_id": request_id, "rule_ids": rule_ids})
            ownership_request = AccountModel.get_request_by_id(request_id)
            for rule in rules:
                if rule.user_id == current_user.id or current_user.is_admin():
                    # Update the rule ownership
                    rule.user_id = ownership_request.user_id

                    requests_list_to_refused = AccountModel.get_all_requests_one_rule_with_rule_id(rule.id)
                    if requests_list_to_refused:
                        for request_ in requests_list_to_refused:
                            if request_.status == "pending":
                                request_.status = "rejected"
                                request_.user_id_to_send = ownership_request.user_id
                    
                    requests_list_to_refused_source = AccountModel.get_all_requests_with_source(ownership_request.rule_source)
                    if requests_list_to_refused_source:
                        for request__ in requests_list_to_refused_source:
                            if request__.status == "pending":
                                request__.status = "rejected"
                                request__.user_id_to_send = ownership_request.user_id


                    # #Save the rule with the new ownership
                    # requests_list_to_update = AccountModel.get_all_requests_with_rule_id(rule.id)
                    # if requests_list_to_update:
                    #     for request_ in requests_list_to_update:
                    #         request_.user_id_to_send = ownership_request.user_id
                    # requests_list_to_update_source = AccountModel.get_all_requests_with_source(ownership_request.rule_source)
                    # if requests_list_to_update_source:
                    #         for request__ in requests_list_to_update_source:
                    #             request__.user_id_to_send = ownership_request.user_id   
                

            flash(f"Request Accepted! {len(rules)} rules are impacted", "success")
        else:
            if updated:
                log_activity("admin.request_rejected",
                             f"Rejected ownership request id={request_id}",
                             extra={"request_id": request_id})
            flash('Request decline with success!', 'success')
        return jsonify({"success": updated}), 200 if updated else 400
    else:
        return jsonify({"success": False}), 500


# about us page
@home_blueprint.route("/about")
def about() -> render_template:
    return render_template("/about_us.html")

# version
@home_blueprint.route("/version")
def version() -> jsonify:
    version = get_version()
    return jsonify({"version": version }), 200

##############
#   ADMIN   #
#############


BACKUP_DIR = os.path.join(os.getcwd(), "backup", "dumps")

@home_blueprint.route('/admin/get_backups', methods=['GET'])
def get_backups():
    if not current_user.is_admin():
        return render_template('access_denied.html')
    return render_template('admin/download_instance.html')

@home_blueprint.route('/admin/backups', methods=['GET'])
@login_required
def list_backups():
    try:
        if not current_user.is_admin():
            return jsonify({"error": "Unauthorized"}), 401
        files = [f for f in os.listdir(BACKUP_DIR) if f.endswith('.dump')]
        files.sort(reverse=True)
        return jsonify({"files": files, "success": True, "toast_class": "success-subtle", "message": "Success"}), 200
    except Exception as e:
        return jsonify({"message": str(e), "error": str(e), "success": False, "toast_class": "danger-subtle"}), 500

@home_blueprint.route('/admin/backups/download/<filename>', methods=['GET'])
@login_required
def download_backup(filename):
    if not current_user.is_admin():
        return jsonify({"error": "Unauthorized"}), 401
    if ".." in filename or filename.startswith("/"):
        abort(400)
    return send_from_directory(BACKUP_DIR, filename, as_attachment=True)


@home_blueprint.route('/admin/vulnerabilities/update', methods=['GET'])
@login_required
def UpdateVulnerabilities():
    if not current_user.is_admin():
        return jsonify({"error": "Unauthorized", "toast_class": "danger-subtle", "message": "Unauthorized"}), 401
    success , msg = RuleModel.migrate_rule_cve_to_json()
    if not success:
        return jsonify({"success": success, "message": msg, "toast_class": "danger-subtle"}), 500
    return jsonify({"success": success, "message": msg, "toast_class": "success-subtle"}), 200

@home_blueprint.route('/admin/similar_rules', methods=['GET'])
@login_required
def similar_rules():
    if not current_user.is_admin():
        return render_template('access_denied.html')
    return render_template('admin/similar_rule_update.html')

@home_blueprint.route("/history_logo")
def history_logo() -> render_template:
    return render_template("macros/history_logo.html")




@home_blueprint.route('/doc/<path:filename>')
def serve_doc_images(filename):
    doc_path = os.path.join(home_blueprint.root_path, '../doc')
    return send_from_directory(doc_path, filename)


######################
#   Activity Logs    #
######################

@home_blueprint.route('/admin/logs', methods=['GET'])
@login_required
def admin_logs():
    if not current_user.is_admin():
        return render_template('access_denied.html')
    return render_template('admin/logs.html')


@home_blueprint.route('/admin/get_logs_page', methods=['GET'])
@login_required
def get_logs_page():
    if not current_user.is_admin():
        return jsonify({"error": "Unauthorized"}), 401

    from app.core.db_class.db import ActivityLog
    from app import db

    page      = request.args.get('page', 1, type=int)
    per_page  = request.args.get('per_page', 50, type=int)
    search    = request.args.get('search', '', type=str).strip()
    action    = request.args.get('action', '', type=str).strip()
    user_id_f = request.args.get('user_id', None, type=int)

    q = ActivityLog.query
    if search:
        q = q.filter(ActivityLog.description.ilike(f'%{search}%'))
    if action:
        q = q.filter(ActivityLog.action.ilike(f'%{action}%'))
    if user_id_f:
        q = q.filter(ActivityLog.user_id == user_id_f)

    q = q.order_by(ActivityLog.created_at.desc())
    paginated = q.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "logs":        [l.to_json() for l in paginated.items],
        "total":       paginated.total,
        "page":        page,
        "per_page":    per_page,
        "total_pages": paginated.pages,
    }), 200


@home_blueprint.route('/admin/logs/delete/<int:log_id>', methods=['POST'])
@login_required
def delete_log(log_id):
    if not current_user.is_admin():
        return jsonify({"error": "Unauthorized"}), 401

    from app.core.db_class.db import ActivityLog
    from app import db

    entry = ActivityLog.query.get(log_id)
    if not entry:
        return jsonify({"success": False, "message": "Log not found"}), 404
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"success": True, "message": "Log deleted"}), 200


@home_blueprint.route('/admin/logs/delete_bulk', methods=['POST'])
@login_required
def delete_logs_bulk():
    """Create a background job to mass-delete logs."""
    if not current_user.is_admin():
        return jsonify({"error": "Unauthorized"}), 401

    data   = request.get_json() or {}
    ids    = data.get('ids', [])
    all_   = data.get('delete_all', False)
    action = data.get('action_filter', '')

    if not ids and not all_:
        return jsonify({"success": False, "message": "No logs selected"}), 400

    from app.features.jobs.jobs_core import create_job
    payload = {"log_ids": ids, "delete_all": all_, "action_filter": action}
    job = create_job(
        job_type   = 'delete_activity_logs',
        payload    = payload,
        label      = f"Delete {len(ids) if ids else 'all'} activity log(s)",
        created_by = current_user.id,
    )
    if not job:
        return jsonify({"success": False, "message": "Failed to create job"}), 500

    log_activity("admin.logs_bulk_delete",
                 f"Scheduled bulk deletion of {len(ids) if ids else 'all'} log(s)",
                 extra=payload)
    return jsonify({"success": True, "message": "Deletion job queued", "job": job.to_json()}), 200


@home_blueprint.route('/activity_feed', methods=['GET'])
def activity_feed():
    """Public activity feed — only is_public=True entries whose target is still accessible."""
    from app.core.db_class.db import ActivityLog, Rule, Bundle
    from app import db

    page     = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 50)

    def _is_accessible(log):
        tt = log.target_type
        if tt == 'rule':
            r = (Rule.query.filter_by(uuid=log.target_uuid).first() if log.target_uuid
                 else Rule.query.get(log.target_id) if log.target_id else None)
            return r is not None and not r.is_deleted
        if tt == 'bundle':
            b = (Bundle.query.filter_by(uuid=log.target_uuid).first() if log.target_uuid
                 else Bundle.query.get(log.target_id) if log.target_id else None)
            return b is not None and b.access
        if tt == 'comment':
            extra = log.extra or {}
            r = (Rule.query.filter_by(uuid=extra['rule_uuid']).first() if extra.get('rule_uuid')
                 else Rule.query.get(extra['rule_id']) if extra.get('rule_id') else None)
            return r is not None and not r.is_deleted
        if tt == 'bundle_comment':
            extra = log.extra or {}
            b = (Bundle.query.filter_by(uuid=extra['bundle_uuid']).first() if extra.get('bundle_uuid')
                 else Bundle.query.get(extra['bundle_id']) if extra.get('bundle_id') else None)
            return b is not None and b.access
        return True  # user, tag, job, github — always visible

    # Fetch a larger batch to absorb entries whose target became private/deleted
    batch_size = per_page * 4
    offset     = (page - 1) * per_page
    candidates = (ActivityLog.query
                  .filter_by(is_public=True)
                  .order_by(ActivityLog.created_at.desc())
                  .offset(offset)
                  .limit(batch_size)
                  .all())

    visible = [l for l in candidates if _is_accessible(l)][:per_page]

    return jsonify({
        "logs":        [l.to_json_public() for l in visible],
        "total":       len(visible),
        "page":        page,
        "total_pages": 1,
    }), 200


@home_blueprint.route('/admin/logs/edit/<int:log_id>', methods=['POST'])
@login_required
def edit_log(log_id):
    if not current_user.is_admin():
        return jsonify({"error": "Unauthorized"}), 401

    from app.core.db_class.db import ActivityLog
    from app import db

    entry = ActivityLog.query.get(log_id)
    if not entry:
        return jsonify({"success": False, "message": "Log not found"}), 404

    data = request.get_json() or {}
    if 'description' in data:
        entry.description = data['description']
    if 'is_public' in data:
        entry.is_public = bool(data['is_public'])
    if 'icon' in data:
        entry.icon = data['icon']
    db.session.commit()
    return jsonify({"success": True, "log": entry.to_json()}), 200


@home_blueprint.route('/admin/logs/actions', methods=['GET'])
@login_required
def get_log_actions():
    """Return the distinct action types present in the log."""
    if not current_user.is_admin():
        return jsonify({"error": "Unauthorized"}), 401

    from app.core.db_class.db import ActivityLog
    from app import db

    actions = [r[0] for r in db.session.query(ActivityLog.action).distinct().order_by(ActivityLog.action).all()]
    return jsonify({"actions": actions}), 200


###########################
#   Admin Settings section #
###########################

@home_blueprint.route('/admin/settings', methods=['GET'])
@login_required
def admin_settings():
    if not current_user.is_admin():
        abort(403)
    return render_template('admin/settings.html')


@home_blueprint.route('/admin/settings/system', methods=['GET'])
@login_required
def admin_settings_system():
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    from .features.admin import admin_core as AdminModel
    return jsonify(AdminModel.get_system_info())


@home_blueprint.route('/admin/settings/packages', methods=['GET'])
@login_required
def admin_settings_packages():
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    from .features.admin import admin_core as AdminModel
    return jsonify(AdminModel.get_installed_packages())


@home_blueprint.route('/admin/settings/submodules', methods=['GET'])
@login_required
def admin_settings_submodules():
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    from .features.admin import admin_core as AdminModel
    return jsonify(AdminModel.get_git_submodules())


@home_blueprint.route('/admin/settings/submodule/update', methods=['POST'])
@login_required
def admin_settings_submodule_update():
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    from .features.admin import admin_core as AdminModel
    data = request.get_json() or {}
    paths = data.get('paths', [])
    if not paths:
        return jsonify({'success': False, 'error': 'No paths provided'}), 400
    results = {path: AdminModel.update_submodule(path) for path in paths}
    log_activity('admin.submodule_update', f"Updated {len(paths)} submodule(s): {', '.join(paths)}")
    return jsonify({'success': True, 'results': results})


@home_blueprint.route('/admin/settings/config', methods=['GET'])
@login_required
def admin_settings_config():
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    from .features.admin import admin_core as AdminModel
    return jsonify(AdminModel.get_app_config())


@home_blueprint.route('/admin/settings/update_env', methods=['POST'])
@login_required
def admin_settings_update_env():
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    from .features.admin import admin_core as AdminModel
    data = request.get_json() or {}
    key = data.get('key', '').strip()
    value = data.get('value', '').strip()
    if key not in AdminModel._ENV_ALLOWED:
        return jsonify({'success': False, 'message': 'Key not allowed.'})
    ok = AdminModel.write_env_value(key, value)
    if ok:
        # Apply immediately to running config for everything except SECRET_KEY
        _NEEDS_RESTART = {'SECRET_KEY'}
        if key not in _NEEDS_RESTART:
            if key == 'MAIL_PORT' or key == 'FLASK_PORT':
                try:
                    current_app.config[key] = int(value)
                except ValueError:
                    pass
            elif key == 'MAIL_USE_TLS' or key == 'MAIL_USE_SSL':
                current_app.config[key] = value.lower() == 'true'
            else:
                current_app.config[key] = value
        log_activity(
            'admin.settings_changed',
            f"Updated {key} via admin settings",
            extra={'key': key, 'requires_restart': key in _NEEDS_RESTART},
        )
    needs_restart = key == 'SECRET_KEY'
    msg = ('Saved. Restart the server to apply the new SECRET_KEY.' if needs_restart and ok
           else 'Saved and applied.' if ok
           else 'Key not allowed or write failed.')
    return jsonify({'success': ok, 'message': msg})


@home_blueprint.route('/admin/settings/test_email', methods=['POST'])
@login_required
def admin_settings_test_email():
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    from .features.admin import admin_core as AdminModel
    data = request.get_json() or {}
    recipient = data.get('recipient', '').strip()
    if not recipient:
        return jsonify({'success': False, 'error': 'No recipient provided'}), 400
    result = AdminModel.send_test_email(recipient)
    if result.get('success'):
        log_activity('admin.test_email_sent', f"Test email sent to {recipient}")
    return jsonify(result)


@home_blueprint.route('/admin/settings/generate_key', methods=['POST'])
@login_required
def admin_settings_generate_key():
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    from .features.admin import admin_core as AdminModel
    key = AdminModel.generate_secret_key()
    return jsonify({'success': True, 'key': key})


@home_blueprint.route('/admin/settings/instance', methods=['GET'])
@login_required
def admin_settings_instance():
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    from .core.db_class.db import InstanceConfig
    cfg = InstanceConfig.query.first()
    if not cfg:
        return jsonify({'exists': False})
    reported_url = cfg.public_url or (
        f"http://{current_app.config.get('FLASK_URL', '127.0.0.1')}"
        f":{current_app.config.get('FLASK_PORT', 7009)}"
    )
    return jsonify({
        'exists':            True,
        'endpoint_uuid':     cfg.uuid,
        'telemetry_enabled': cfg.telemetry_enabled,
        'public_url':        cfg.public_url,
        'reported_url':      reported_url,
        'version':           cfg.version,
        'last_started_at':   cfg.last_started_at.strftime('%Y-%m-%d %H:%M:%S') if cfg.last_started_at else None,
        'created_at':        cfg.created_at.strftime('%Y-%m-%d %H:%M:%S') if cfg.created_at else None,
        'is_official':       current_app.config.get('IS_OFFICIAL_INSTANCE', False),
        'telemetry_url':     'https://rulezet.org/api/instance/register',
    })


@home_blueprint.route('/admin/settings/instance/init', methods=['POST'])
@login_required
def admin_settings_instance_init():
    """Generate / refresh endpoint_uuid, version, last_started_at in InstanceConfig."""
    if not current_user.is_admin():
        return jsonify({'error': 'Unauthorized'}), 403
    import uuid as _uuid_mod
    import datetime as _dt
    from app import db
    from .core.db_class.db import InstanceConfig
    from .core.utils.activity_log import log_activity

    cfg = InstanceConfig.query.first()
    if not cfg:
        cfg = InstanceConfig(
            uuid=str(_uuid_mod.uuid4()),
            telemetry_enabled=True,
            public_url=current_app.config.get('INSTANCE_PUBLIC_URL'),
        )
        db.session.add(cfg)
        db.session.flush()

    reported_url = cfg.public_url or (
        f"http://{current_app.config.get('FLASK_URL', '127.0.0.1')}"
        f":{current_app.config.get('FLASK_PORT', 7009)}"
    )
    cfg.uuid            = str(_uuid_mod.uuid5(_uuid_mod.NAMESPACE_URL, reported_url))
    cfg.version         = current_app.config.get('APP_VERSION', 'unknown')
    cfg.last_started_at = _dt.datetime.utcnow()
    db.session.commit()
    log_activity('admin.instance_init', 'Instance config initialized/refreshed from admin settings')
    return jsonify({
        'success':         True,
        'endpoint_uuid':   cfg.uuid,
        'version':         cfg.version,
        'last_started_at': cfg.last_started_at.strftime('%Y-%m-%d %H:%M:%S'),
    })


@home_blueprint.route('/admin/logs/set_visibility', methods=['POST'])
@login_required
def set_logs_visibility():
    """Bulk-set is_public on a list of activity log entries."""
    if not current_user.is_admin():
        return jsonify({"error": "Unauthorized"}), 401

    from app.core.db_class.db import ActivityLog
    from app import db

    data      = request.get_json() or {}
    ids       = data.get('ids', [])
    is_public = bool(data.get('is_public', False))

    if not ids:
        return jsonify({"success": False, "message": "No IDs provided"}), 400

    updated = ActivityLog.query.filter(ActivityLog.id.in_(ids)).update(
        {"is_public": is_public}, synchronize_session=False
    )
    db.session.commit()
    return jsonify({"success": True, "updated": updated}), 200