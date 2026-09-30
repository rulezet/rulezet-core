# ------------------------------------------------------------------------------------------------------------------- #
#                                       PRIVATE ENDPOINT (auth required)                                              #
# ------------------------------------------------------------------------------------------------------------------- #
#
# Every route here needs a valid X-API-KEY (403 otherwise) and runs as the
# key's owner (see decorators.api_required): logs and bundle history name
# that user. Route names and existing parameters are a public contract —
# new parameters are only ever added, and always optional.

from flask_restx import Namespace, Resource
from flask import  request
from flask_login import current_user
from sqlalchemy import func, or_

from app import db
from app.features.bundle import bundle_core as BundleModel
from app.core.utils.decorators import api_required
from app.core.utils.activity_log import log_activity
from app.core.db_class.db import Bundle, Rule, Tag
from .bundle_public_api import bundle_structure_json, MAX_PER_PAGE

bundle_private_ns = Namespace(
    "Private action on Bundle 🔑 (with api key)",
    description="Private bundle operations"
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _payload():
    """JSON body, else query string — every POST here accepts both."""
    return request.get_json(silent=True) or request.args.to_dict()


def _is_manager(bundle):
    return current_user.id == bundle.user_id or current_user.is_admin()


def _as_list(value):
    """A list from a JSON list or a comma-separated string."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (int, str)):
        return [v.strip() for v in str(value).split(",") if v.strip()]
    return None


def _resolve_rules(rule_ids=None, rule_uuids=None):
    """(rules, missing) — active rules for the given ids / uuids, in the
    order given; `missing` lists the references that match no active rule."""
    rules, missing, seen = [], [], set()
    refs = [(str(r).strip(), "id") for r in rule_ids or []] + [(str(r).strip(), "uuid") for r in rule_uuids or []]
    for ref_s, kind in refs:
        if not ref_s:
            continue
        if kind == "id":
            rule = Rule.query.filter(Rule.id == int(ref_s), Rule.is_deleted == False).first() \
                if ref_s.isdigit() else None
        else:
            rule = Rule.query.filter(Rule.uuid == ref_s, Rule.is_deleted == False).first()
        if rule is None:
            missing.append(ref_s)
        elif rule.id not in seen:
            seen.add(rule.id)
            rules.append(rule)
    return rules, missing


def _resolve_tags(values):
    """(tag_ids, unknown) from tag names (case-insensitive) or ids."""
    ids, unknown = [], []
    for v in values or []:
        v_s = str(v).strip()
        if not v_s:
            continue
        tag = Tag.query.get(int(v_s)) if v_s.isdigit() else \
            Tag.query.filter(func.lower(Tag.name) == v_s.lower()).first()
        if tag is None:
            unknown.append(v_s)
        elif tag.id not in ids:
            ids.append(tag.id)
    return ids, unknown


def _bundle_from_params(data):
    """Bundle from `bundle_id` or (optional alternative) `bundle_uuid`."""
    bundle_id = data.get("bundle_id")
    if bundle_id not in (None, ""):
        return BundleModel.get_bundle_by_ref(bundle_id), True
    bundle_uuid = data.get("bundle_uuid")
    if bundle_uuid:
        return BundleModel.get_bundle_by_ref(bundle_uuid), True
    return None, False


#############
#   Create  #
#############

@bundle_private_ns.route('/create')
@bundle_private_ns.doc(
    description="""
Create a new bundle in the system. You must authenticate using your **API KEY**, which can be found in your personal profile on rulezet.org.

### Body Parameters (JSON)

| Parameter       | Type          | Required | Description                                                     | Constraints / Notes                            |
|-----------------|---------------|----------|-----------------------------------------------------------------|-------------------------------------------------|
| X-API-KEY       | string (header)| Yes     | Your personal API key for authentication                        | Must be valid. Found in your user profile      |
| name            | string        | Yes      | Name of the bundle                                              | Non-empty                                       |
| description     | string        | No       | Description of the bundle                                       | Defaults to empty                               |
| public          | bool          | No       | Allow people to see your bundle or not                          | Strict boolean, defaults to `true`              |
| vulnerabilities | list[string]  | No       | Vulnerability identifiers (e.g. `["CVE-2024-1234"]`)            |                                                 |
| tags            | list          | No       | Tag names (e.g. `"tlp:clear"`) or tag ids                       | Every tag must exist, else 400                  |
| rule_ids        | list[int]     | No       | Rules to put in the bundle (by id)                              | Every rule must exist, else 400                 |
| rule_uuids      | list[string]  | No       | Rules to put in the bundle (by uuid)                            | Every rule must exist, else 400                 |
| folder          | string        | No       | Folder path for those rules in the bundle tree (e.g. `sigma/windows`) | Defaults to `Unsorted`                  |

### Response

`message`, `bundle_id`, `uuid`, `rules_added`.

### Example cURL Request

```bash
curl -X POST /api/bundle/private/create \\
-H "Content-Type: application/json" \\
-H "X-API-KEY: <YOUR_API_KEY>" \\
-d '{
    "name": "My Bundle Name",
    "description": "This is a test bundle created via API.",
    "public": true,
    "tags": ["tlp:clear"],
    "rule_uuids": ["6f1c…"],
    "folder": "detections"
}'
```

This endpoint allows authenticated users to create a new bundle for organizing rules. The name is required, everything else is optional.
"""
)
class CreateBundle(Resource):
    @api_required
    @bundle_private_ns.doc(params={
        "name": "Required. The name of the bundle. Must be a non-empty string.",
        "description": "Optional. Description of the bundle.",
        "public": "Optional. Boolean flag indicating if the bundle is public. Defaults to True.",
        "vulnerabilities": "Optional. List of vulnerability identifiers.",
        "tags": "Optional. List of tag names or ids.",
        "rule_ids": "Optional. List of rule ids to add.",
        "rule_uuids": "Optional. List of rule uuids to add.",
        "folder": "Optional. Folder path for the added rules (default: Unsorted).",
    })
    def post(self):
        """Create a new bundle"""
        user = current_user
        data = _payload()

        # --- Validate name ---
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            return {"message": "Invalid bundle", "error": "'name' must be a non-empty string"}, 400
        name = name.strip()

        # --- Validate public (strict boolean only) ---
        public = data.get("public", True)
        if not isinstance(public, bool):
            return {"message": "Invalid bundle", "error": "'public' must be a boolean"}, 400

        # --- Validate description ---
        description = data.get("description", "")
        if description is not None and not isinstance(description, str):
            return {"message": "Invalid bundle", "error": "'description' must be a string"}, 400
        description = description.strip() if description else ""

        # --- Optional extras, all validated before anything is created ---
        vulns = _as_list(data.get("vulnerabilities"))
        tags = _as_list(data.get("tags"))
        rule_ids = _as_list(data.get("rule_ids"))
        rule_uuids = _as_list(data.get("rule_uuids"))
        folder = data.get("folder")
        for field, value in (("vulnerabilities", vulns), ("tags", tags),
                             ("rule_ids", rule_ids), ("rule_uuids", rule_uuids)):
            if value is None:
                return {"message": "Invalid bundle", "error": f"'{field}' must be a list"}, 400
        if folder is not None and not isinstance(folder, str):
            return {"message": "Invalid bundle", "error": "'folder' must be a string"}, 400

        tag_ids, unknown_tags = _resolve_tags(tags)
        if unknown_tags:
            return {"message": "Invalid bundle", "error": "Unknown tag(s)", "unknown_tags": unknown_tags}, 400
        rules, missing_rules = _resolve_rules(rule_ids, rule_uuids)
        if missing_rules:
            return {"message": "Invalid bundle", "error": "Rule(s) not found", "missing_rules": missing_rules}, 400

        # --- Create bundle ---
        my_bundle = BundleModel.create_bundle(
            {"name": name, "description": description, "public": public,
             "vulnerability_identifiers": [str(v).strip() for v in vulns if str(v).strip()]},
            user
        )
        if not my_bundle:
            return {"message": "Failed to create bundle"}, 500

        if tag_ids:
            BundleModel.update_bundle_tags(my_bundle.id, tag_ids, user)
        if rules:
            _add_rules(my_bundle, rules, folder, "Added via API")

        log_activity(
            "bundle.create",
            f"Created bundle '{my_bundle.name}' via API",
            target_type="bundle", target_id=my_bundle.id, target_uuid=my_bundle.uuid,
            extra={"source": "api", "user_id": user.id, "public": public, "rules": len(rules)},
            is_public=bool(public),   # a private bundle never shows in the public feed
        )

        return {
            "message": "Bundle created successfully",
            "bundle_id": my_bundle.id,
            "uuid": my_bundle.uuid,
            "rules_added": len(rules),
        }, 200


def _add_rules(bundle, rules, folder=None, description=None):
    """Attach rules (skipping ones already in the bundle) and give each a
    place in the folder tree. Returns the number of newly attached rules."""
    from app.core.db_class.db import BundleRuleAssociation
    import datetime
    from app.features.bundle.bundle_history_core import track_bundle_change
    with track_bundle_change(bundle.id, "rules", user=current_user):
        existing = {rid for (rid,) in db.session.query(BundleRuleAssociation.rule_id)
                    .filter(BundleRuleAssociation.bundle_id == bundle.id)}
        added = 0
        for rule in rules:
            if rule.id in existing:
                continue
            db.session.add(BundleRuleAssociation(
                bundle_id=bundle.id, rule_id=rule.id, description=description,
                added_at=datetime.datetime.now(tz=datetime.timezone.utc),
            ))
            added += 1
        db.session.flush()
        BundleModel.place_rules_in_structure(bundle.id, [r.id for r in rules], folder)
        db.session.commit()
    return added


#################
#   add rules   #
#################

@bundle_private_ns.route('/add_rule_bundle')
@bundle_private_ns.doc(
    description="""
Add a rule to an existing bundle. This operation requires authentication using your **API KEY**, which can be retrieved from your account profile.

The rule is also placed in the bundle's folder tree (in `folder`, default `Unsorted`), so it shows up in the
bundle's Structure tab and in every download.

### Query Parameters (GET) — or JSON body (POST)

| Parameter     | Type   | Required | Description                                                    | Constraints / Notes                              |
|---------------|--------|----------|----------------------------------------------------------------|--------------------------------------------------|
| X-API-KEY     | string (header) | Yes | Your personal API key for authentication                  | Must be valid. Provided in your user profile     |
| rule_id       | int    | Yes*     | ID of the rule to add to the bundle                           | Must exist                                       |
| rule_uuid     | string | No       | Alternative to `rule_id`: the rule's uuid                     | *One of `rule_id` / `rule_uuid`                  |
| bundle_id     | int    | Yes*     | ID of the bundle that will receive the rule                   | Must exist and you must own it (or be admin)     |
| bundle_uuid   | string | No       | Alternative to `bundle_id`: the bundle's uuid                 | *One of `bundle_id` / `bundle_uuid`              |
| description   | string | Yes      | A description or comment for this rule inside the bundle      | Must be non-empty string                         |
| folder        | string | No       | Folder path in the bundle tree (e.g. `sigma/windows`)         | Created if missing. Defaults to `Unsorted`       |

### Permission Requirements

You may add a rule to a bundle **only if**:
- You are the **owner** of the bundle, **or**
- You are an **administrator**

If you do not meet these conditions, the request will be rejected (401).

### Errors

| Status | Meaning |
|--------|---------|
| 400    | Missing parameter |
| 401    | Not the owner / an admin |
| 403    | Missing or invalid API key |
| 404    | Bundle not found, or rule not found / deleted |

### Example cURL Request

```bash
curl -X GET "/api/bundle/private/add_rule_bundle?rule_id=42&bundle_id=7&description=Important" \\
     -H "X-API-KEY: <YOUR_API_KEY>"

curl -X POST "/api/bundle/private/add_rule_bundle" -H "X-API-KEY: <YOUR_API_KEY>" \\
     -H "Content-Type: application/json" \\
     -d '{"rule_uuid": "6f1c…", "bundle_uuid": "a2b4…", "description": "Important", "folder": "yara"}'
```
"""
)
class AddRuleToBundle(Resource):
    _PARAMS = {
        "rule_id": "Required (or rule_uuid). ID of the rule to add.",
        "rule_uuid": "Optional. UUID of the rule to add (instead of rule_id).",
        "bundle_id": "Required (or bundle_uuid). ID of the bundle.",
        "bundle_uuid": "Optional. UUID of the bundle (instead of bundle_id).",
        "description": "Required. Description for this rule within the bundle.",
        "folder": "Optional. Folder path in the bundle tree (default: Unsorted).",
    }

    @bundle_private_ns.doc(params=_PARAMS)
    @api_required
    def get(self):
        """Add a rule to a bundle"""
        return self._add(request.args.to_dict())

    @bundle_private_ns.doc(params=_PARAMS)
    @api_required
    def post(self):
        """Add a rule to a bundle (JSON body)"""
        return self._add(_payload())

    @staticmethod
    def _add(data):
        description = data.get("description")
        rule_ref = data.get("rule_id") or data.get("rule_uuid")
        bundle, has_bundle_ref = _bundle_from_params(data)

        if not rule_ref or not has_bundle_ref or not description:
            return {
                "success": False,
                "message": "Missing rule_id or bundle_id or description",
                "toast_class": "danger"
            }, 400

        if not bundle:
            return {
                "success": False,
                "message": "Bundle not found",
                "toast_class": "danger"
            }, 404

        if not _is_manager(bundle):
            return {
                "success": False,
                "message": "You don't have the permission to do that!",
                "toast_class": "danger"
            }, 401

        if data.get("rule_id"):
            rules, _ = _resolve_rules(rule_ids=[str(data["rule_id"])])
        else:
            rules, _ = _resolve_rules(rule_uuids=[data["rule_uuid"]])
        if not rules:
            return {
                "success": False,
                "message": "Rule not found",
                "toast_class": "danger"
            }, 404
        rule = rules[0]

        folder = data.get("folder") if isinstance(data.get("folder"), str) else None
        _add_rules(bundle, [rule], folder, str(description))
        log_activity(
            "bundle.rule_added",
            f"Added rule id={rule.id} to bundle '{bundle.name}' (id={bundle.id}) via API",
            target_type="bundle", target_id=bundle.id, target_uuid=bundle.uuid,
            extra={"rule_id": rule.id, "source": "api"},
            is_public=False,
        )
        return {
            "success": True,
            "message": "Rule added!",
            "toast_class": "success"
        }, 200

    # curl -X GET "http://127.0.0.1:7009/api/bundle/add_rule_bundle?rule_id=42&bundle_id=7&description=Important" \
    #     -H "X-API-KEY: user_api_key"


#######################
#   add rules (bulk)  #
#######################

@bundle_private_ns.route('/add_rules_bundle')
@bundle_private_ns.doc(
    description="""
Add **several rules** to a bundle in one call. Rules already in the bundle are skipped.
Each added rule is placed in the bundle's folder tree (`folder`, default `Unsorted`).

### Body Parameters (JSON)

| Parameter   | Type          | Required | Description                                              |
|-------------|---------------|----------|----------------------------------------------------------|
| bundle_id   | int           | Yes*     | ID of the bundle (*or `bundle_uuid`)                     |
| bundle_uuid | string        | No       | UUID of the bundle                                       |
| rule_ids    | list[int]     | Yes*     | Rules to add by id (*at least one of `rule_ids` / `rule_uuids`) |
| rule_uuids  | list[string]  | No       | Rules to add by uuid                                     |
| folder      | string        | No       | Folder path in the bundle tree (e.g. `sigma/windows`)    |
| description | string        | No       | Comment stored with each added rule                      |

Owner of the bundle or admin only. Unknown / deleted rules are reported in `missing_rules`
and do not block the others.

### Response

`success`, `added` (newly attached rules), `already_present`, `missing_rules`.

### Example cURL Request

```bash
curl -X POST "/api/bundle/private/add_rules_bundle" -H "X-API-KEY: <YOUR_API_KEY>" \\
     -H "Content-Type: application/json" \\
     -d '{"bundle_id": 7, "rule_ids": [1, 2, 3], "folder": "windows"}'
```
"""
)
class AddRulesToBundle(Resource):
    @api_required
    def post(self):
        """Add several rules to a bundle"""
        data = _payload()
        bundle, has_bundle_ref = _bundle_from_params(data)
        rule_ids = _as_list(data.get("rule_ids"))
        rule_uuids = _as_list(data.get("rule_uuids"))
        if rule_ids is None or rule_uuids is None:
            return {"success": False, "message": "'rule_ids' and 'rule_uuids' must be lists"}, 400
        if not has_bundle_ref or not (rule_ids or rule_uuids):
            return {"success": False, "message": "Missing bundle_id and rule_ids / rule_uuids"}, 400
        if not bundle:
            return {"success": False, "message": "Bundle not found"}, 404
        if not _is_manager(bundle):
            return {"success": False, "message": "You don't have the permission to do that!"}, 401
        folder = data.get("folder")
        if folder is not None and not isinstance(folder, str):
            return {"success": False, "message": "'folder' must be a string"}, 400

        rules, missing = _resolve_rules(rule_ids, rule_uuids)
        added = _add_rules(bundle, rules, folder, data.get("description") or "Added via API") if rules else 0
        if added:
            log_activity(
                "bundle.rule_added",
                f"Added {added} rule(s) to bundle '{bundle.name}' (id={bundle.id}) via API",
                target_type="bundle", target_id=bundle.id, target_uuid=bundle.uuid,
                extra={"rule_ids": [r.id for r in rules], "source": "api"},
                is_public=False,
            )
        return {
            "success": True,
            "message": f"{added} rule(s) added",
            "added": added,
            "already_present": len(rules) - added,
            "missing_rules": missing,
        }, 200


##################
# remove rules   #
##################

@bundle_private_ns.route('/remove_rule_bundle')
@bundle_private_ns.doc(
    description="""
Remove a rule from a bundle.

This endpoint allows removing an existing rule from a specific bundle — it is also taken out of the
bundle's folder tree. Only the bundle owner or an administrator is allowed to perform this action.

### Query Parameters (GET) — or JSON body (POST)

| Parameter   | Type   | Required | Description                                                  |
|-------------|--------|----------|--------------------------------------------------------------|
| rule_id     | int    | Yes*     | ID of the rule to remove from the bundle (*or `rule_uuid`)   |
| rule_uuid   | string | No       | UUID of the rule (instead of `rule_id`)                      |
| bundle_id   | int    | Yes*     | ID of the bundle (*or `bundle_uuid`)                         |
| bundle_uuid | string | No       | UUID of the bundle (instead of `bundle_id`)                  |

### Errors

| Status | Meaning |
|--------|---------|
| 400    | Missing parameter |
| 401    | Not the owner / an admin |
| 403    | Missing or invalid API key |
| 404    | Bundle not found, or the rule is not in this bundle |

### Example Request

```bash
curl -X GET "/api/bundle/private/remove_rule_bundle?rule_id=123&bundle_id=456" -H "X-API-KEY: <YOUR_API_KEY>"
```
""")
class RemoveRuleFromBundle(Resource):
    _PARAMS = {
        'rule_id': 'ID of the rule to remove',
        'rule_uuid': 'Optional. UUID of the rule (instead of rule_id)',
        'bundle_id': 'ID of the bundle to remove the rule from',
        'bundle_uuid': 'Optional. UUID of the bundle (instead of bundle_id)',
    }

    @bundle_private_ns.doc(params=_PARAMS)
    @api_required
    def get(self):
        """Remove a rule from a bundle"""
        return self._remove(request.args.to_dict())

    @bundle_private_ns.doc(params=_PARAMS)
    @api_required
    def post(self):
        """Remove a rule from a bundle (JSON body)"""
        return self._remove(_payload())

    @staticmethod
    def _remove(data):
        rule_ref = data.get("rule_id") or data.get("rule_uuid")
        bundle, has_bundle_ref = _bundle_from_params(data)

        # ---- Validate input ----
        if not rule_ref or not has_bundle_ref:
            return {
                "success": False,
                "message": "Missing rule_id or bundle_id",
                "toast_class": "danger"
            }, 400

        # ---- Lookup bundle ----
        if not bundle:
            return {
                "success": False,
                "message": "Bundle not found",
                "toast_class": "danger"
            }, 404

        # ---- Permission check ----
        if not _is_manager(bundle):
            return {
                "success": False,
                "message": "You don't have the permission to do that!",
                "toast_class": "danger"
            }, 401

        # ---- Resolve the rule (a trashed rule can still be removed) ----
        if data.get("rule_id"):
            rule_id = int(data["rule_id"]) if str(data["rule_id"]).isdigit() else None
        else:
            rule = Rule.query.filter_by(uuid=str(data["rule_uuid"]).strip()).first()
            rule_id = rule.id if rule else None

        # ---- Remove rule ----
        if rule_id and BundleModel.remove_rule_from_bundle(bundle.id, rule_id):
            log_activity(
                "bundle.rule_removed",
                f"Removed rule id={rule_id} from bundle '{bundle.name}' (id={bundle.id}) via API",
                target_type="bundle", target_id=bundle.id, target_uuid=bundle.uuid,
                extra={"rule_id": rule_id, "source": "api"},
                is_public=False,
            )
            return {
                "success": True,
                "message": "Rule removed!",
                "toast_class": "success"
            }, 200

        return {
            "success": False,
            "message": "Rule not found in this bundle or already removed",
            "toast_class": "danger"
        }, 404


####################
#   Edit bundle    #
####################

@bundle_private_ns.route('/edit_bundle/<int:bundle_id>')
@bundle_private_ns.doc(description="""
Update a bundle. **Only the fields you send are changed** — anything left out keeps its current value.

### Body Parameters (JSON)

| Parameter       | Type          | Required | Description                                                          |
|-----------------|---------------|----------|----------------------------------------------------------------------|
| name            | string        | No       | New name (non-empty)                                                 |
| description     | string        | No       | New description                                                      |
| public          | bool          | No       | Visibility (strict boolean)                                          |
| vulnerabilities | list[string]  | No       | Replaces the vulnerability identifiers (`[]` clears them)            |
| tags            | list          | No       | Replaces the tags — tag names or ids (`[]` removes them all)         |

Owner of the bundle or admin only (401 otherwise).

### Errors

| Status | Meaning |
|--------|---------|
| 400    | Invalid field type, empty name, unknown tag, or no field to update |
| 401    | Not the owner / an admin |
| 403    | Missing or invalid API key |
| 404    | Bundle not found |

### Example cURL Request

```bash
curl -X POST http://127.0.0.1:7009/api/bundle/private/edit_bundle/1 \\
    -H "Content-Type: application/json" \\
    -H "X-API-KEY: <YOUR_API_KEY>" \\
    -d '{"name": "Updated Bundle Name", "tags": ["tlp:green"]}'
```
""", params={
    'bundle_id': 'ID of the bundle'
})
class EditBundle(Resource):
    @api_required
    def post(self, bundle_id):
        """Update a bundle"""
        bundle = BundleModel.get_bundle_by_id(bundle_id)
        if not bundle:
            return {"success": False, "message": "Bundle not found"}, 404
        if not _is_manager(bundle):
            return {"success": False, "message": "You don't have the permission to do that!"}, 401

        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return {"success": False, "message": "A JSON object body is required", "toast_class": "danger"}, 400

        changes = {}
        if "name" in data:
            if not isinstance(data["name"], str) or not data["name"].strip():
                return {"success": False, "message": "'name' must be a non-empty string", "toast_class": "danger"}, 400
            changes["name"] = data["name"].strip()
        if "description" in data:
            if data["description"] is not None and not isinstance(data["description"], str):
                return {"success": False, "message": "'description' must be a string", "toast_class": "danger"}, 400
            changes["description"] = (data["description"] or "").strip()
        if "public" in data:
            if not isinstance(data["public"], bool):
                return {"success": False, "message": "'public' must be a boolean", "toast_class": "danger"}, 400
            changes["public"] = data["public"]
        if "vulnerabilities" in data:
            vulns = _as_list(data["vulnerabilities"])
            if vulns is None:
                return {"success": False, "message": "'vulnerabilities' must be a list", "toast_class": "danger"}, 400
            changes["vulnerabilities"] = [str(v).strip() for v in vulns if str(v).strip()]
        tag_ids = None
        if "tags" in data:
            tags = _as_list(data["tags"])
            if tags is None:
                return {"success": False, "message": "'tags' must be a list", "toast_class": "danger"}, 400
            tag_ids, unknown = _resolve_tags(tags)
            if unknown:
                return {"success": False, "message": "Unknown tag(s)", "unknown_tags": unknown, "toast_class": "danger"}, 400

        if not changes and tag_ids is None:
            return {"success": False, "message": "Nothing to update", "toast_class": "danger"}, 400

        success = BundleModel.update_bundle(bundle_id, changes) if changes else bundle
        if success and tag_ids is not None:
            success = BundleModel.update_bundle_tags(bundle_id, tag_ids, current_user)
        if success:
            log_activity(
                "bundle.edit",
                f"Edited bundle '{bundle.name}' (id={bundle_id}) via API",
                target_type="bundle", target_id=bundle_id, target_uuid=bundle.uuid,
                extra={"source": "api", "changes": {k: v for k, v in changes.items()
                                                     if k in ("name", "description", "public")},
                       **({"tag_ids": tag_ids} if tag_ids is not None else {})},
                is_public=False,
            )
            return {
                "success": True,
                "message": "Bundle updated successfully",
                "toast_class": "success"
            }, 200
        return {
            "success": False,
            "message": "Update failed",
            "toast_class": "danger"
        }, 500

    # curl -X POST http://127.0.0.1:7009/api/bundle/edit_bundle/1 \
    #     -H "Content-Type: application/json" \
    #     -H "X-API-KEY: user_api_key" \
    #     -d '{"name": "Updated Bundle Name", "description": "New description here"}'


####################
#   Structure      #
####################

@bundle_private_ns.route('/<string:bundle_ref>/structure')
@bundle_private_ns.doc(description="""
**Replace** the folder tree of a bundle (same result as saving in the bundle editor).

`bundle_ref` is the bundle **id** or **uuid**. Owner of the bundle or admin only.

The tree also defines **which rules are in the bundle**: rules not placed in it are removed from the bundle,
rules placed in it are added. Tip: read the current tree with `GET /api/bundle/public/<bundle_ref>/structure`,
edit it, send it back.

### Body (JSON)

`{"structure": [ <node>, ... ]}` — nodes:

| type     | Fields                                   | Description                                  |
|----------|------------------------------------------|----------------------------------------------|
| folder   | `name`, `children`                       | A folder (nested nodes in `children`)        |
| file     | `name`, `content`                        | A custom text file (README.md, notes…)       |
| rule     | `rule_id` **or** `rule_uuid`, `name` (optional) | A rule placed at this spot            |

Limits (same as the editor): 5000 nodes, 20 folder levels, 1 MB per file, 20 MB of files in total;
names 1-255 characters without `/`.

### Errors

| Status | Meaning |
|--------|---------|
| 400    | Invalid tree, or a referenced rule does not exist (`missing_rules`) |
| 401    | Not the owner / an admin |
| 403    | Missing or invalid API key |
| 404    | Bundle not found |

### Example cURL Request

```bash
curl -X POST "/api/bundle/private/7/structure" -H "X-API-KEY: <YOUR_API_KEY>" \\
     -H "Content-Type: application/json" \\
     -d '{"structure": [
           {"type": "file", "name": "README.md", "content": "# My bundle"},
           {"type": "folder", "name": "windows", "children": [{"type": "rule", "rule_id": 42}]}
         ]}'
```
""", params={'bundle_ref': 'Bundle id or uuid'})
class EditBundleStructure(Resource):
    @api_required
    def post(self, bundle_ref):
        """Replace the folder tree of a bundle"""
        from app.features.bundle.bundle_history_core import track_bundle_change
        bundle = BundleModel.get_bundle_by_ref(bundle_ref)
        if not bundle:
            return {"success": False, "message": "Bundle not found"}, 404
        if not _is_manager(bundle):
            return {"success": False, "message": "You don't have the permission to do that!"}, 401

        data = request.get_json(silent=True) or {}
        structure = data.get("structure")
        if not isinstance(structure, list):
            return {"success": False, "message": "'structure' must be a list of nodes"}, 400

        # API node format → editor format (rules by local id)
        missing = []

        def convert(nodes, depth=1):
            out = []
            if depth > BundleModel.MAX_DEPTH + 1:
                return out
            for node in nodes:
                if not isinstance(node, dict):
                    out.append(node)   # let validate_structure reject it
                    continue
                if node.get("type") == "rule" or node.get("rule_id") or node.get("rule_uuid"):
                    ref = node.get("rule_id") or node.get("rule_uuid")
                    if node.get("rule_id") is not None:
                        rules, _ = _resolve_rules(rule_ids=[str(node["rule_id"])])
                    else:
                        rules, _ = _resolve_rules(rule_uuids=[node.get("rule_uuid")])
                    if not rules:
                        missing.append(str(ref))
                        continue
                    out.append({"type": "file", "name": node.get("name") or rules[0].title or "rule",
                                "rule_id": rules[0].id})
                elif node.get("type") == "folder":
                    children = node.get("children") or []
                    out.append({"type": "folder", "name": node.get("name"),
                                "children": convert(children, depth + 1) if isinstance(children, list) else children})
                else:
                    out.append({"type": node.get("type"), "name": node.get("name"),
                                "content": node.get("content") or ""})
            return out

        converted = convert(structure)
        if missing:
            return {"success": False, "message": "Rule(s) not found", "missing_rules": missing}, 400
        error = BundleModel.validate_structure(converted)
        if error:
            return {"success": False, "message": error}, 400

        with track_bundle_change(bundle.id, "structure", user=current_user):
            ok = BundleModel.update_bundle_from_structure(bundle.id, converted)
            ok = ok and BundleModel.save_workspace(bundle.id, converted)
        if not ok:
            return {"success": False, "message": "Error saving the structure"}, 500

        log_activity(
            "bundle.edit",
            f"Replaced the structure of bundle '{bundle.name}' (id={bundle.id}) via API",
            target_type="bundle", target_id=bundle.id, target_uuid=bundle.uuid,
            extra={"source": "api", "action": "save_structure"},
            is_public=False,
        )
        return {"success": True, "message": "Structure saved",
                "structure": bundle_structure_json(bundle.id)}, 200


####################
#   Delete bundle  #
####################

@bundle_private_ns.route('/delete_bundle/<string:bundle_ref>')
@bundle_private_ns.doc(description="""
Delete a bundle **permanently** (its tree, notes, releases and history go with it; the rules themselves are kept).

`bundle_ref` is the bundle **id** or **uuid**. Owner of the bundle or admin only.

### Errors

| Status | Meaning |
|--------|---------|
| 401    | Not the owner / an admin |
| 403    | Missing or invalid API key |
| 404    | Bundle not found |

### Example cURL Request

```bash
curl -X POST "/api/bundle/private/delete_bundle/7" -H "X-API-KEY: <YOUR_API_KEY>"
```
""", params={'bundle_ref': 'Bundle id or uuid'})
class DeleteBundle(Resource):
    @api_required
    def post(self, bundle_ref):
        """Delete a bundle"""
        bundle = BundleModel.get_bundle_by_ref(bundle_ref)
        if not bundle:
            return {"success": False, "message": "Bundle not found"}, 404
        if not _is_manager(bundle):
            return {"success": False, "message": "You don't have the permission to do that!"}, 401
        bundle_id, bundle_name, bundle_uuid = bundle.id, bundle.name, bundle.uuid
        if not BundleModel.delete_bundle(bundle_id):
            return {"success": False, "message": "Delete failed"}, 500
        log_activity("bundle.delete", f"Deleted bundle '{bundle_name}' (id={bundle_id}) via API",
                     target_type="bundle", target_id=bundle_id, target_uuid=bundle_uuid,
                     extra={"source": "api"})
        return {"success": True, "message": "Bundle deleted", "bundle_id": bundle_id}, 200


####################
#   My bundles     #
####################

@bundle_private_ns.route('/my_bundles')
@bundle_private_ns.doc(description="""
List **your** bundles — private ones included — newest first, paginated.

### Query Parameters

| Parameter | Type   | Required | Description                                     |
|-----------|--------|----------|-------------------------------------------------|
| search    | string | No       | Keyword in the bundle name or description       |
| page      | int    | No       | Page number (default 1)                         |
| per_page  | int    | No       | Bundles per page (default 20, max 200)          |

### Response

`bundle_list`, `page`, `per_page`, `total`, `total_pages`.

### Example cURL Request

```bash
curl -G "/api/bundle/private/my_bundles" -d page=1 -H "X-API-KEY: <YOUR_API_KEY>"
```
""")
class MyBundles(Resource):
    @bundle_private_ns.doc(params={
        "search": "Optional. Keyword in name / description",
        "page": "Optional. Page number (default 1)",
        "per_page": "Optional. Bundles per page (default 20, max 200)",
    })
    @api_required
    def get(self):
        """List your bundles (private included)"""
        page = max(1, request.args.get("page", 1, type=int))
        per_page = min(MAX_PER_PAGE, max(1, request.args.get("per_page", 20, type=int)))
        query = Bundle.query.filter(Bundle.user_id == current_user.id)
        search = (request.args.get("search") or "").strip()
        if search:
            like = f"%{search}%"
            query = query.filter(or_(Bundle.name.ilike(like), Bundle.description.ilike(like)))
        pagination = (query.order_by(Bundle.created_at.desc(), Bundle.id.desc())
                      .paginate(page=page, per_page=per_page, error_out=False))
        return {
            "message": f"{pagination.total} bundle(s) found",
            "bundle_list": [b.to_json() for b in pagination.items],
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "total_pages": pagination.pages,
        }, 200
