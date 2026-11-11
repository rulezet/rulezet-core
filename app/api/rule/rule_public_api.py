# ------------------------------------------------------------------------------------------------------------------- #
#                                               PUBLIC ENDPOINT                                                       #
# ------------------------------------------------------------------------------------------------------------------- #

import json
from typing import Optional
from flask import request, url_for
from flask_restx import Resource, Namespace

from app.api.utils.rule_validation import *

from app import cache, memory_cache
from app.core.utils.page_cache import api_cached
from app.core.utils import utils
from app.features.misp.rule.misp_object import get_rule_misp_object
from ...features.rule import rule_core as RuleModel
from ...features.account import account_core as AccountModel
from flask_restx import Namespace, Resource


rule_public_ns = Namespace(
    "Public action on Rule ✅",
    description="Public rule operations"
)

###################################
#       search rules Page         #
###################################

@rule_public_ns.route('/searchPage')
@rule_public_ns.doc(
    description="""
Search for rules by **title**, **description**, **UUID**, or **author**, with pagination support.

### Query Parameters

| Parameter  | Type    | Description                                                                 |
|------------|---------|-----------------------------------------------------------------------------|
| search     | string  | Keyword to search in rule title                                              |
| author     | string  | Filter rules by author                                                       |
| rule_type  | string  | Filter by rule type                                                          |
| sort_by    | string  | Sorting option: `newest`, `oldest`, `most_likes`, `least_likes`             |
| page       | integer | Page number (default=1)                                                     |
| per_page   | integer | Items per page (default=10)                                                 |

### Example cURL Request


```bash
curl -G "http://127.0.0.1:7009/api/rule/public/searchPage" \
--data-urlencode "search=detect" \
--data-urlencode "author=John" \
--data-urlencode "sort_by=newest" \
--data-urlencode "page=1" \
--data-urlencode "per_page=10"
```
"""
)
@rule_public_ns.route('/searchPage')
class SearchRulePage(Resource):

    @api_cached('search_page')
    @rule_public_ns.doc(params={
        "search": "Keyword to search in rule title",
        "author": "Filter rules by author",
        "rule_type": "Filter by rule type",
        "sort_by": "Sorting option: newest, oldest, most_likes, least_likes",
        "page": "Page number (default=1)",
        "per_page": "Items per page (default=10)"
    })
    def get(self):
        """
        Search and paginate rules.
        """

        # Get query params
        search = request.args.get("search")
        author = request.args.get("author")
        sort_by = request.args.get("sort_by")
        rule_type = request.args.get("rule_type")

        page = request.args.get("page", default=1, type=int)
        per_page = request.args.get("per_page", default=10, type=int)


        # ------------
        #  Validation
        # ------------

        try:
            validate_search_param(search)
            validate_author_param(author)
            validate_sort_by_param(sort_by, allowed_sort={"newest", "oldest", "most_likes", "least_likes"})
            verify_rule_format(rule_type)
            validate_page_param(page)
            validate_per_page_param(per_page)
        except ValueError as e:
            return {"error": str(e)}, 400

        # Query filtered rules
        query = RuleModel.filter_rules(search=search, author=author, sort_by=sort_by, rule_type=rule_type)
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        # Prepare base arguments (keep filters but remove pagination)
        args = request.args.to_dict(flat=False)
        args.pop("page", None)
        args.pop("per_page", None)

        # Dynamic endpoint (auto-detect)
        endpoint = request.endpoint

        # Build next/prev URLs
        next_url = (
            url_for(endpoint, page=pagination.next_num, per_page=per_page,
                    _external=True, **args)
            if pagination.has_next else None
        )

        prev_url = (
            url_for(endpoint, page=pagination.prev_num, per_page=per_page,
                    _external=True, **args)
            if pagination.has_prev else None
        )

        # Serialize results
        results = []
        for rule in pagination.items:
            results.append({
                "uuid": rule.uuid,
                "title": rule.title,
                "description": rule.description,
                "author": rule.author,
                "creation_date": rule.creation_date.isoformat(),
                "format": rule.format,
                "content": rule.to_string,
                "is_code_format": rule.is_code_format(),
            })

        # Final response
        return {
            "total_rules_found": pagination.total,
            "total_pages": pagination.pages,
            "pagination": {
                "prev_page": prev_url,
                "current_page": pagination.page,
                "next_page": next_url,
            },
            "results": results,
        }, 200



###################################
#   search rules (no pagination)  #
###################################
@rule_public_ns.route('/search')
@rule_public_ns.doc(
    description="""
Search for rules by **title**, **description**, **UUID**, or **author**, without pagination.

### Query Parameters

| Parameter  | Type    | Description                                                                 |
|------------|---------|-----------------------------------------------------------------------------|
| search     | string  | Keyword to search in rule title                                              |
| author     | string  | Filter rules by author                                                       |
| rule_type  | string  | Filter by rule type                                                          |
| sort_by    | string  | Sorting option: `newest`, `oldest`, `most_likes`, `least_likes`             |

### Example cURL Request

```bash
curl -G "http://127.0.0.1:7009/api/rule/public/search" \
     --data-urlencode "search=detect" \
     --data-urlencode "author=@malgamy12" \
     --data-urlencode "rule_type=malware" \
     --data-urlencode "sort_by=newest"

"""
)
class SearchRule(Resource):
    @api_cached('search')
    @rule_public_ns.doc(params={
    "search": "Keyword to search in rule title",
    "author": "Filter rules by author",
    "rule_type": "Filter by rule type",
    "sort_by": "Sorting option: newest, oldest, most_likes, least_likes",
    })
    def get(self):
        """
        Search rules without pagination.
        """
        # Retrieve query parameters
        search = request.args.get("search")
        author = request.args.get("author")
        sort_by = request.args.get("sort_by")
        rule_type = request.args.get("rule_type")


        # ------------
        #  Validation
        # ------------

        try:
            validate_search_param(search)
            validate_author_param(author)
            validate_sort_by_param(sort_by, allowed_sort={"newest", "oldest", "most_likes", "least_likes"})
            verify_rule_format(rule_type)
        except ValueError as e:
            return {"error": str(e)}, 400
        # Filter rules
        query = RuleModel.filter_rules(search=search,author=author,sort_by=sort_by, rule_type=rule_type)
        # Serialize results
        results = [
            {
                "uuid": rule.uuid,
                "title": rule.title,
                "description": rule.description,
                "author": rule.author,
                "creation_date": rule.creation_date.isoformat(),
                "format": rule.format,
                "content": rule.to_string
            }
            for rule in query
        ]

        # Return results
        return {
            "total_rules_found": len(results),
            "results": results,
        }, 200


##################################
#   search rules  convert MISP   #
##################################

@rule_public_ns.route('/Convert_MISP')
@rule_public_ns.doc(
    description="""
Search for rules by **title**, **description**, **UUID**, or **author** and convert them into MISP objects if possible.

### Query Parameters

| Parameter  | Type    | Description                                                                 |
|------------|---------|-----------------------------------------------------------------------------|
| search     | string  | Keyword to search in rule title                                             |
| author     | string  | Filter rules by author                                                      |
| rule_type  | string  | Filter by rule type                                                         |
| sort_by    | string  | Sorting option: `newest`, `oldest`, `most_likes`, `least_likes`             |

### Example cURL Request

```bash
curl -G "http://127.0.0.1:7009/api/rule/public/Convert_MISP" \
--data-urlencode "search=mars" \
--data-urlencode "author=John" \
--data-urlencode "rule_type=malware" \
--data-urlencode "sort_by=newest"
```
"""
)
class ConvertMISP(Resource):
    @rule_public_ns.doc(params={
    "search": "Keyword to search in rule title",
    "author": "Filter rules by author",
    "rule_type": "Filter by rule type",
    "sort_by": "Sorting option: newest, oldest, most_likes, least_likes"
    })
    def get(self):
        """
        Search rules and convert them to MISP objects if possible.
        """
        search = request.args.get("search")
        author = request.args.get("author")
        sort_by = request.args.get("sort_by")
        rule_type = request.args.get("rule_type")
        
        # ------------
        #  Validation
        # ------------

        try:
            validate_search_param(search)
            validate_author_param(author)
            validate_sort_by_param(sort_by, allowed_sort={"newest", "oldest", "most_likes", "least_likes"})
            verify_rule_format(rule_type)
        except ValueError as e:
            return {"error": str(e)}, 400

        query = RuleModel.filter_rules(search=search, author=author, sort_by=sort_by, rule_type=rule_type)

        def convert_rule(rule_id: int) -> Optional[dict]:
            try:
                return get_rule_misp_object(rule_id) or None   # already a dict
            except Exception:
                return None

        results = []
        for rule in query:
            misp_obj = convert_rule(rule.id)
            results.append({
                "uuid": rule.uuid,
                "title": rule.title,
                "description": rule.description,
                "author": rule.author,
                "creation_date": rule.creation_date.isoformat(),
                "format": rule.format,
                "content": rule.to_string,
                "misp_object": misp_obj
            })

        return {
            "total_rules_found": len(results),
            "results": results,
        }, 200
    
#############################
#   Get all rule's info     #
#############################

@rule_public_ns.route('/detail/<int:rule_id>')
@rule_public_ns.doc(
    description="""
Retrieve the full details of a rule using its **unique rule ID**.

### Path Parameter

| Parameter | Type | Description                       |
|-----------|------|-----------------------------------|
| rule_id   | int  | The ID of the rule to retrieve    |

### Example cURL Request

```bash
curl -X GET "http://127.0.0.1:7009/api/rule/public/detail/6"
```
"""
)
class DetailRule(Resource):
    @api_cached('detail', rule_arg='rule_id')
    def get(self, rule_id):
        """
        Get the details of a rule by its ID.
        """
        # Retrieve rule (a rule in the trash is not public any more)
        rule = RuleModel.get_rule(rule_id)
        if not rule or rule.is_deleted:
            return {"message": "Rule not found"}, 404

        # Retrieve author
        author = AccountModel.get_user(rule.user_id)
        if not author:
            return {"message": "User not found"}, 404

        # Return full rule details
        return {
            "id": rule.id,
            "title": rule.title,
            "format": rule.format,
            "version": rule.version,
            "to_string": rule.to_string,
            "description": rule.description or "No description for the rule",
            # rule.author is the free-text author, not a User
            "source": rule.source or rule.author or f"{author.first_name} {author.last_name}".strip(),
            "license": rule.license,
            "cve_id": rule.cve_id,                                    # unchanged (raw stored text)
            "cve_ids": RuleModel._parse_vulnerabilities(rule.cve_id),   # the same, as a real list
            "original_uuid": rule.original_uuid,
            "uuid": rule.uuid,
            "creation_date": rule.creation_date.isoformat() if rule.creation_date else None,
            # full precision: send it back as base_last_modif when editing (POST /api/rule/private/edit/<id>)
            "last_modif": rule.last_modif.isoformat() if rule.last_modif else None,
            "tags": sorted({a.tag.name for a in rule.rule_tags_assocs if a.tag}),
            "attacks": sorted({a.technique_id for a in rule.attack_assocs if a.technique_id}),
            "user": {
                "id": author.id,
                "first_name": author.first_name,
                "last_name": author.last_name
            }
        }, 200

    #############################
    #   Get all rules by user   #
    #############################

@rule_public_ns.route('/all_by_user/<int:user_id>')
@rule_public_ns.doc(
    description="""
Retrieve **all rules authored by a specific user**, identified by their unique `user_id`.

### Path Parameter

| Parameter | Type | Description                           |
|-----------|------|---------------------------------------|
| user_id   | int  | The ID of the user whose rules to get |

### Example cURL Request

```bash
curl -X GET "http://127.0.0.1:7009/api/rule/public/all_by_user/4"
```
"""
)
class RulesByUser(Resource):
    def get(self, user_id):
        """
        Get all rules created by a specific user.
        """
        # Fetch user
        user = AccountModel.get_user(user_id)
        if not user:
            return {"message": "User not found"}, 404

        # Fetch rules authored by the user
        rules = RuleModel.get_all_rules_by_user(user_id)
        if not rules:
            return {
                "message": "No rules found for this user",
                "rules": [],
                "success": True
            }, 200

        # Serialize rules
        result = []
        for rule in rules:
            result.append({
                "id": rule.id,
                "title": rule.title,
                "format": rule.format,
                "version": rule.version,
                "to_string": rule.to_string,
                "description": rule.description or "No description for the rule",
                "source": rule.source or f"{user.first_name}, {user.last_name}",
                "license": rule.license,
                "cve_id": rule.cve_id,
                "original_uuid": rule.original_uuid,
                "user": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name
                }
            })

        return {
            "message": f"{len(result)} rules found for user {user.first_name} {user.last_name}",
            "rules": result,
            "success": True
        }, 200


    ##############################
    #   Get all rules by CVE id  #
    ##############################


@rule_public_ns.route('/search_rules_by_cve')
@rule_public_ns.doc(
    description="""
Search for all rules that match specific **CVE IDs** or **vulnerability identifiers** (GHSA, PYSEC, etc.).

This endpoint automatically detects and normalizes vulnerability patterns from the input string, then performs a broad search across the rules database.

### Query Parameter

| Parameter | Type   | Description                                                                 |
|-----------|--------|-----------------------------------------------------------------------------|
| cve_ids   | string | A comma-separated list or a raw string containing one or more vulnerability IDs |

### Example cURL Request

```bash
curl -G "http://127.0.0.1:7009/api/rule/public/search_rules_by_cve" \
    --data-urlencode "cve_ids=CVE-2021-44228,GHSA-j8v8-6h6r-m6pq"

""",
params={'cve_ids': 'One or more vulnerability identifiers (CVE, GHSA, etc.)'} ) 

class RulesByCVE(Resource):
    # Same route, same request params, same JSON shape — an external
    # vulnerability-lookup tool calls this heavily and depends on the exact
    # response format. Caching by cve_ids (query_string=True) just avoids
    # re-running the underlying full-table ILIKE scan for a repeat/near-
    # simultaneous lookup of the same identifiers; a fresh scan still runs
    # for anything not seen in the last 60s.
    @memory_cache.cached(timeout=60, query_string=True)
    def get(self):
        """ Search rules by vulnerability identifiers """
        raw_input = request.args.get('cve_ids', '') 
        if not raw_input: 
            return {"error": "No IDs provided."}, 400
        # utils.detect_cve returns (True, '["CVE-XXXX"]')
        success, cve_json = utils.detect_cve(raw_input)
        
        if not success:
            return {"error": "Detection failed."}, 500

        # Load the JSON string into a Python list
        cve_patterns = json.loads(cve_json)
        
        if not cve_patterns:
            return {"error": "No valid identifiers detected."}, 404

        # Search the database using the cleaned list
        result = RuleModel.search_rules_by_cve_patterns(cve_patterns)

        return {
            "detected_patterns": cve_patterns,
            "total_matches": result.get("total_all_rules", 0),
            "stats": result.get("totals", 0),
            "results": result.get("rules", [])
        }, 200


    ###########################################
    #   Get all rules by ATT&CK technique id  #
    ###########################################


@rule_public_ns.route('/search_rules_by_attack')
@rule_public_ns.doc(
    description="""
Search for all rules mapped to specific **MITRE ATT&CK technique IDs** (e.g. T1059, T1059.001).

This endpoint automatically detects and normalizes technique identifiers from the input string, then performs a broad search across the rules database.

### Query Parameter

| Parameter      | Type   | Description                                                            |
|----------------|--------|-------------------------------------------------------------------------|
| technique_ids  | string | A comma-separated list or a raw string containing one or more technique IDs |

### Example cURL Request

```bash
curl -G "http://127.0.0.1:7009/api/rule/public/search_rules_by_attack" \
    --data-urlencode "technique_ids=T1059,T1059.001"

""",
params={'technique_ids': 'One or more MITRE ATT&CK technique identifiers'} )

class RulesByAttackTechnique(Resource):
    def get(self):
        """ Search rules by MITRE ATT&CK technique identifiers """
        raw_input = request.args.get('technique_ids', '')
        if not raw_input:
            return {"error": "No IDs provided."}, 400
        # utils.detect_attack_technique returns (True, '["T1059"]')
        success, technique_json = utils.detect_attack_technique(raw_input)

        if not success:
            return {"error": "Detection failed."}, 500

        technique_patterns = json.loads(technique_json)

        if not technique_patterns:
            return {"error": "No valid identifiers detected."}, 404

        result = RuleModel.search_rules_by_attack_patterns(technique_patterns)

        return {
            "detected_patterns": technique_patterns,
            "total_matches": result.get("total_all_rules", 0),
            "stats": result.get("totals", 0),
            "results": result.get("rules", [])
        }, 200


    ###########################################
    #   Validate rule syntax (dry run)        #
    ###########################################


MAX_VALIDATE_CONTENT = 512 * 1024   # public endpoint: one rule, not a corpus


@rule_public_ns.route('/dependencies/<int:rule_id>')
@rule_public_ns.doc(
    description="""
The rules a rule **needs** to work (transitively: what those need too) and the rules that
need it — YARA rules used in its condition, Wazuh `if_sid` parents, Sigma correlation
bases, Kunai `rule()`, manual "depends on" links. Use it to import a rule together with
everything it needs.

### Response

```json
{
  "rule_id": 12,
  "requires": [ {"id": 7, "uuid": "…", "title": "…", "format": "yara", "depth": 1,
                 "via": 12, "version": "1.0", "last_modif": "…", "to_string": "rule A { … }"} ],
  "required_by": [ {"id": 30, "uuid": "…", "title": "…", "format": "yara", "depth": 1, "via": 12} ],
  "edges": [ {"from": 12, "to": 7, "type": "yara_condition_ref"} ],
  "install_order": [7, 12],
  "truncated": false
}
```

`edges`: `from` needs `to`. `install_order`: the rule and the rules it requires, each after
the rules it needs (the order a single YARA file must declare them in).

### Example cURL Request

```bash
curl -X GET "http://127.0.0.1:7009/api/rule/public/dependencies/12"
```
"""
)
class RuleDependencies(Resource):
    def get(self, rule_id):
        """Rules this rule needs, and rules that need it"""
        from app.features.rule_relation.rule_relation_core import get_dependency_graph, dependency_install_order
        from app.core.db_class.rule import Rule

        rule = RuleModel.get_rule(rule_id)
        if not rule or rule.is_deleted:
            return {"message": "Rule not found"}, 404

        graph = get_dependency_graph(rule_id)
        required_ids = [n["id"] for n in graph["nodes"] if n["role"] == "requires"]
        rules = {r.id: r for r in RuleModel._active().filter(Rule.id.in_(required_ids)).all()} if required_ids else {}

        def _node(n, with_content):
            out = {k: n[k] for k in ("id", "uuid", "title", "format", "depth", "via")}
            r = rules.get(n["id"])
            if with_content and r:
                out.update(version=r.version, to_string=r.to_string,
                           last_modif=r.last_modif.isoformat() if r.last_modif else None)
            return out

        requires = [_node(n, True) for n in graph["nodes"] if n["role"] == "requires" and n["id"] in rules]
        required_by = [_node(n, False) for n in graph["nodes"] if n["role"] == "required_by"]
        install_ids = [rule_id] + [n["id"] for n in requires]
        return {
            "rule_id": rule_id,
            "requires": requires,
            "required_by": required_by,
            "edges": graph["edges"],
            "install_order": dependency_install_order(install_ids, graph["edges"]),
            "truncated": graph["truncated"],
        }, 200


@rule_public_ns.route('/validate')
@rule_public_ns.doc(
    description="""
Check whether a rule's content is **syntactically valid** for a given format — the same
per-format check a rule goes through on creation/import, run here as a dry run: nothing
is saved, no rule is created (max 512 KB). A YARA rule referencing other rules by name
(e.g. in its condition) is compiled together with those rules, as on the web Create / Edit
pages — only rules that can be trusted to be the intended ones (see `rule_id` / `X-API-KEY`).

### JSON body

| Field    | Type   | Description                                                              |
|----------|--------|---------------------------------------------------------------------------|
| format   | string | Rule format, e.g. yara, sigma, suricata, zeek, wazuh, nse, crs, nova, splunk, elastic, sagan, kql, atr, kunai |
| content  | string | The rule's raw content to validate                                       |
| rule_id  | int    | Optional. The rule this content edits: rules of the same source / GitHub path, or linked to it, can be compiled in |

Optional header `X-API-KEY`: your own rules can be compiled in too. Without either, a
referenced rule is not looked up (a rule with the same name could be anyone's).

### Example cURL Request

```bash
curl -X POST "http://127.0.0.1:7009/api/rule/public/validate" \
    -H "Content-Type: application/json" \
    -d '{"format": "sigma", "content": "title: Example\\nlogsource:\\n  category: process_creation\\n..."}'
```
""",
)
class ValidateRule(Resource):
    def post(self):
        """ Validate a rule's syntax without creating it """
        payload = request.get_json(silent=True) or {}
        rule_format = (payload.get("format") or "").strip()
        content = payload.get("content") or ""

        if not rule_format:
            return {"error": "No format provided."}, 400
        if not content.strip():
            return {"error": "No content provided."}, 400
        if len(content) > MAX_VALIDATE_CONTENT:
            return {"error": f"Content too large (max {MAX_VALIDATE_CONTENT // 1024} KB)."}, 413

        result = RuleModel.validate_rule_syntax(rule_format, content)
        if result is None:
            return {"error": f"Unknown or unsupported format: {rule_format}"}, 404
        # A rule referencing others (YARA: a rule name in the condition) fails on its own
        # with "undefined identifier": look the referenced rules up in Rulezet and compile
        # again with them, like the web Create / Edit pages. Only on that failure, so a
        # plain check stays one compile.
        if not result.ok and any('undefined identifier' in str(e) for e in (result.errors or [])):
            # Only trusted rules are compiled in (never just "a rule with that name"): the
            # rules of the API key's user, and — with rule_id, the rule being edited — the
            # rules of the same source / GitHub path or already linked to it.
            trust = {}
            api_user = utils.get_user_from_api(request.headers) if request.headers.get("X-API-KEY") else None
            if api_user:
                trust["owner_ids"] = (api_user.id,)
            edited = None
            rule_id = payload.get("rule_id")
            if isinstance(rule_id, int) and not isinstance(rule_id, bool):
                edited = RuleModel.get_rule(rule_id)
            if edited and not edited.is_deleted:
                trust.update(rule_id=edited.id, source=edited.source, github_path=edited.github_path)
                trust["owner_ids"] = tuple({*trust.get("owner_ids", ()), edited.user_id})
            resolved = RuleModel.validate_rule_syntax(rule_format, content, resolve_dependencies=True, **trust)
            if resolved is not None:
                result = resolved

        return {
            "format": rule_format,
            "valid": bool(result.ok),
            "errors": result.errors or [],
            "warnings": result.warnings or [],
        }, 200