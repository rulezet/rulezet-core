from flask import request, send_file
from flask_restx import Namespace, Resource
from flask_login import current_user

from ...features.bundle import bundle_core as BundleModel
from app.core.utils.decorators import api_optional
from app.core.db_class.db import Bundle, BundleNode, BundleRelease, Rule

bundle_public_ns = Namespace(
    "Public action on Bundle ✅",
    description="Public bundle operations"
)


# ── Shared helpers (also used by bundle_private_api) ─────────────────────────

MAX_PER_PAGE = 200
_SHARE_KEY_DOC = "Optional. Share key of a private bundle (needs your X-API-KEY too)"


def _holds_share_key(bundle):
    """The caller sent this private bundle's *current* share key (?share_key=)
    — same rule as the web share link: only for an identified user (valid
    X-API-KEY), and regenerating / revoking the link invalidates it."""
    import hmac
    key = (request.args.get("share_key") or "").strip()
    if not key or not bundle.share_token or len(key) > 64:
        return False
    if not current_user.is_authenticated:
        return False
    return hmac.compare_digest(key, bundle.share_token)


def viewable_bundle_or_error(bundle_ref):
    """(bundle, None) or (None, (json, status)) for a bundle id or uuid.
    Public bundles are readable by anyone. A private one only by its owner,
    an admin (both identified by their X-API-KEY), or a user holding the
    bundle's current share key (X-API-KEY + ?share_key=)."""
    bundle = BundleModel.get_bundle_by_ref(bundle_ref)
    if not bundle:
        return None, ({"success": False, "message": "Bundle not found"}, 404)
    if not BundleModel.can_view_bundle(bundle) and not _holds_share_key(bundle):
        return None, ({"success": False, "message": "Access denied"}, 403)
    return bundle, None


def bundle_structure_json(bundle_id):
    """The folder tree for API consumers: folders, custom files (with their
    content) and rules (id, uuid, format). Trashed rules are left out."""
    nodes = BundleNode.query.filter_by(bundle_id=bundle_id).order_by(BundleNode.id).all()
    if not nodes:
        return []
    rule_ids = {n.rule_id for n in nodes if n.rule_id}
    rules = {}
    if rule_ids:
        for rid, r_uuid, title, fmt in (Rule.query.with_entities(Rule.id, Rule.uuid, Rule.title, Rule.format)
                                        .filter(Rule.id.in_(rule_ids), Rule.is_deleted == False)):
            rules[rid] = (r_uuid, title, fmt)
    children = {}
    for n in nodes:
        children.setdefault(n.parent_id, []).append(n)

    def to_json(n):
        if n.rule_id:
            info = rules.get(n.rule_id)
            if not info:
                return None
            return {"type": "rule", "name": info[1], "rule_id": n.rule_id, "rule_uuid": info[0], "format": info[2]}
        if n.node_type == "folder":
            return {"type": "folder", "name": n.name,
                    "children": [c for c in (to_json(x) for x in children.get(n.id, [])) if c]}
        return {"type": "file", "name": n.name, "content": n.custom_content or ""}

    return [c for c in (to_json(n) for n in children.get(None, [])) if c]


def bundle_detail_json(bundle):
    data = bundle.to_json()
    rules = BundleModel.get_rules_from_bundle(bundle.id)
    data.update({
        "tags": [t.get("name") for t in BundleModel.get_tags_for_bundle_json(bundle.id)],
        "rules": [{"id": r.id, "uuid": r.uuid, "title": r.title, "format": r.format} for r in rules],
        "structure": bundle_structure_json(bundle.id),
        "release_count": BundleRelease.query.filter_by(bundle_id=bundle.id).count(),
    })
    return data


def _page_args():
    page = max(1, request.args.get("page", 1, type=int))
    per_page = min(MAX_PER_PAGE, max(1, request.args.get("per_page", 20, type=int)))
    return page, per_page


#######################
#   search bundles    #
#######################

_SORTS = {
    "newest":    Bundle.created_at.desc(),
    "oldest":    Bundle.created_at.asc(),
    "updated":   Bundle.updated_at.desc(),
    "name":      Bundle.name.asc(),
    "downloads": Bundle.download_count.desc(),
    "views":     Bundle.view_count.desc(),
    "votes":     Bundle.vote_up.desc(),
}


@bundle_public_ns.route('/search')
@bundle_public_ns.doc(
    description="""
Search for public bundles by **name** or **description**.

### Query Parameters

| Parameter  | Type    | Required | Description                                                                 |
|------------|---------|----------|-----------------------------------------------------------------------------|
| search     | string  | No       | Keyword to search in bundle name and description (omit it to list every public bundle) |
| page       | int     | No       | Page number. Without it the full result list is returned (no pagination)   |
| per_page   | int     | No       | Items per page when `page` is given (default 20, max 200)                   |
| sort       | string  | No       | `newest` (default), `oldest`, `updated`, `name`, `downloads`, `views`, `votes` |

### Response

`message`, `bundle_list` — plus `page`, `per_page`, `total`, `total_pages` when `page` is given.

### Example cURL Request

```bash
curl -G "http://127.0.0.1:7009/api/bundle/public/search" --data-urlencode "search=detect"
curl -G "http://127.0.0.1:7009/api/bundle/public/search" -d page=1 -d per_page=50 -d sort=downloads
```
"""
)
class SearchBundle(Resource):
    @bundle_public_ns.doc(params={
        "search": "Optional. Keyword to search in bundle name and description",
        "page": "Optional. Page number — enables pagination",
        "per_page": "Optional. Items per page (default 20, max 200)",
        "sort": "Optional. newest | oldest | updated | name | downloads | views | votes",
    })
    def get(self):
        """
        Search public bundles (optionally paginated).
        """
        search = (request.args.get("search") or "").strip()
        sort = request.args.get("sort", "newest")
        if sort not in _SORTS:
            return {"message": f"Invalid sort '{sort}'", "allowed": list(_SORTS)}, 400

        query = Bundle.query.filter(Bundle.access == True)
        if search:
            like = f"%{search}%"
            query = query.filter(Bundle.name.ilike(like) | Bundle.description.ilike(like))
        query = query.order_by(_SORTS[sort], Bundle.id.desc())

        if request.args.get("page") is None:
            items = query.all()
            return {
                "message": f"{len(items)} bundle(s) found",
                "bundle_list": [b.to_json() for b in items],
            }, 200

        page, per_page = _page_args()
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        return {
            "message": f"{pagination.total} bundle(s) found",
            "bundle_list": [b.to_json() for b in pagination.items],
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "total_pages": pagination.pages,
        }, 200


#######################
#   bundle detail     #
#######################

@bundle_public_ns.route('/detail/<string:bundle_ref>')
@bundle_public_ns.doc(
    description="""
Get everything about a bundle: metadata, tags, vulnerabilities, rules and folder structure.

`bundle_ref` is the bundle **id** or **uuid**. Public bundles are readable by anyone.
A **private** bundle is only returned to its owner or an admin — send your `X-API-KEY` header —
or to a user holding the bundle's **share key** (the `share=` value of its share link): send your
`X-API-KEY` **and** `share_key`. Regenerating or revoking the share link invalidates the key.

### Path / Query Parameters

| Parameter  | Type   | Required | Description                                          |
|------------|--------|----------|------------------------------------------------------|
| bundle_ref | string | Yes      | Bundle id or uuid                                    |
| share_key  | string | No       | Share key of a private bundle (with your `X-API-KEY`) |

### Response

The bundle fields (`id`, `uuid`, `name`, `description`, `author`, `access`, `vulnerability_identifiers`, …) plus:
`tags` (names), `rules` (`id`, `uuid`, `title`, `format`), `structure` (folder tree, see `/structure`), `release_count`.

### Errors

| Status | Meaning |
|--------|---------|
| 403    | Private bundle and you are not its owner / an admin, nor hold its share key |
| 404    | No bundle with this id / uuid |

### Example cURL Request

```bash
curl "http://127.0.0.1:7009/api/bundle/public/detail/12"
curl "http://127.0.0.1:7009/api/bundle/public/detail/6f1c…" -H "X-API-KEY: <YOUR_API_KEY>"
```
"""
)
class BundleDetail(Resource):
    @bundle_public_ns.doc(params={"share_key": _SHARE_KEY_DOC})
    @api_optional
    def get(self, bundle_ref):
        """Get a bundle with its rules, tags and structure"""
        bundle, err = viewable_bundle_or_error(bundle_ref)
        if err:
            return err
        return {"success": True, "bundle": bundle_detail_json(bundle)}, 200


#######################
#   bundle rules      #
#######################

@bundle_public_ns.route('/<string:bundle_ref>/rules')
@bundle_public_ns.doc(
    description="""
List the rules of a bundle, paginated, with their full content and metadata.

`bundle_ref` is the bundle **id** or **uuid**. Private bundle: owner / admin (`X-API-KEY`), or anyone holding its share key (`X-API-KEY` + `share_key`).

### Query Parameters

| Parameter | Type | Required | Description                             |
|-----------|------|----------|-----------------------------------------|
| page      | int  | No       | Page number (default 1)                 |
| per_page  | int  | No       | Rules per page (default 20, max 200)    |

### Response

`rules` (each rule as returned by the rule API), `page`, `per_page`, `total`, `total_pages`.

### Example cURL Request

```bash
curl -G "http://127.0.0.1:7009/api/bundle/public/12/rules" -d page=1 -d per_page=100
```
"""
)
class BundleRules(Resource):
    @bundle_public_ns.doc(params={
        "page": "Optional. Page number (default 1)",
        "per_page": "Optional. Rules per page (default 20, max 200)",
        "share_key": _SHARE_KEY_DOC,
    })
    @api_optional
    def get(self, bundle_ref):
        """List the rules of a bundle (paginated)"""
        bundle, err = viewable_bundle_or_error(bundle_ref)
        if err:
            return err
        from app.core.db_class.db import BundleRuleAssociation
        page, per_page = _page_args()
        pagination = (Rule.query
                      .join(BundleRuleAssociation, BundleRuleAssociation.rule_id == Rule.id)
                      .filter(BundleRuleAssociation.bundle_id == bundle.id, Rule.is_deleted == False)
                      .order_by(Rule.id.asc())
                      .paginate(page=page, per_page=per_page, error_out=False))
        return {
            "success": True,
            "bundle_id": bundle.id,
            "bundle_uuid": bundle.uuid,
            "rules": [r.to_json() for r in pagination.items],
            "page": page,
            "per_page": per_page,
            "total": pagination.total,
            "total_pages": pagination.pages,
        }, 200


#######################
#   bundle structure  #
#######################

@bundle_public_ns.route('/<string:bundle_ref>/structure')
@bundle_public_ns.doc(
    description="""
Get the folder tree of a bundle, as organised in the bundle editor.

`bundle_ref` is the bundle **id** or **uuid**. Private bundle: owner / admin (`X-API-KEY`), or anyone holding its share key (`X-API-KEY` + `share_key`).

### Node format

| Field     | Present on     | Description                                  |
|-----------|----------------|----------------------------------------------|
| type      | all            | `folder`, `file` (custom file) or `rule`     |
| name      | all            | Folder / file name, or rule title            |
| children  | folder         | Nested nodes                                 |
| content   | file           | The file's text content (README, notes…)     |
| rule_id, rule_uuid, format | rule | The rule placed at this spot        |

The same format is accepted by `POST /api/bundle/private/<bundle_ref>/structure`.

### Example cURL Request

```bash
curl "http://127.0.0.1:7009/api/bundle/public/12/structure"
```
"""
)
class BundleStructure(Resource):
    @bundle_public_ns.doc(params={"share_key": _SHARE_KEY_DOC})
    @api_optional
    def get(self, bundle_ref):
        """Get the folder tree of a bundle"""
        bundle, err = viewable_bundle_or_error(bundle_ref)
        if err:
            return err
        return {"success": True, "bundle_id": bundle.id, "bundle_uuid": bundle.uuid,
                "structure": bundle_structure_json(bundle.id)}, 200


#######################
#   bundle download   #
#######################

@bundle_public_ns.route('/<string:bundle_ref>/download')
@bundle_public_ns.doc(
    description="""
Download a bundle as a file — the same exports as the **Download** menu of the bundle page.

`bundle_ref` is the bundle **id** or **uuid**. Private bundle: owner / admin (`X-API-KEY`), or anyone holding its share key (`X-API-KEY` + `share_key`).

### Query Parameters

| Parameter | Type   | Required | Description |
|-----------|--------|----------|-------------|
| part      | string | No       | `full` (default): README, metadata, structure, rules, ATT&CK coverage, MISP event · `rules`: every rule + its JSON · `structure`: the folder tree · `files`: custom files only · `misp`: the bundle as a MISP event (JSON) |
| release   | string | No       | Release id or version (e.g. `v1.2`) — downloads that frozen release instead of the live bundle. Not available with `part=misp` |

### Response

A ZIP file (`application/zip`), or a JSON file for `part=misp`.

### Errors

| Status | Meaning |
|--------|---------|
| 400    | Unknown `part`, empty bundle (`rules`), or `release` with `misp` |
| 403    | Private bundle and you are not its owner / an admin, nor hold its share key |
| 404    | Bundle or release not found, or no custom files (`files`) |

### Example cURL Request

```bash
curl -OJ "http://127.0.0.1:7009/api/bundle/public/12/download?part=full"
curl -OJ "http://127.0.0.1:7009/api/bundle/public/12/download?part=rules&release=v1.0"
```
"""
)
class BundleDownload(Resource):
    @bundle_public_ns.doc(params={
        "part": "Optional. full (default) | rules | structure | files | misp",
        "release": "Optional. Release id or version to download instead of the live bundle",
        "share_key": _SHARE_KEY_DOC,
    })
    @api_optional
    def get(self, bundle_ref):
        """Download a bundle (ZIP or MISP JSON)"""
        from app.features.bundle.bundle import build_bundle_download
        bundle, err = viewable_bundle_or_error(bundle_ref)
        if err:
            return err
        part = (request.args.get("part") or "full").strip().lower()
        payload, name, mimetype, error = build_bundle_download(bundle, part, request.args.get("release"))
        if error:
            return {"success": False, "message": error[0]}, error[1]
        return send_file(payload, as_attachment=True, download_name=name, mimetype=mimetype)


#######################
#   bundle releases   #
#######################

@bundle_public_ns.route('/<string:bundle_ref>/releases')
@bundle_public_ns.doc(
    description="""
List the published releases (frozen versions) of a bundle, newest first.

`bundle_ref` is the bundle **id** or **uuid**. Private bundle: owner / admin (`X-API-KEY`), or anyone holding its share key (`X-API-KEY` + `share_key`).
Download one with `GET /api/bundle/public/<bundle_ref>/download?release=<version>`.

### Response

`releases`: `id`, `uuid`, `version`, `title`, `notes`, `rule_count`, `file_count`, `health_score`, `user_name`, `created_at`.

### Example cURL Request

```bash
curl "http://127.0.0.1:7009/api/bundle/public/12/releases"
```
"""
)
class BundleReleases(Resource):
    @bundle_public_ns.doc(params={"share_key": _SHARE_KEY_DOC})
    @api_optional
    def get(self, bundle_ref):
        """List the releases of a bundle"""
        bundle, err = viewable_bundle_or_error(bundle_ref)
        if err:
            return err
        releases = (BundleRelease.query.filter_by(bundle_id=bundle.id)
                    .order_by(BundleRelease.created_at.desc(), BundleRelease.id.desc()).all())
        return {"success": True, "bundle_id": bundle.id, "bundle_uuid": bundle.uuid,
                "releases": [r.to_json() for r in releases]}, 200
