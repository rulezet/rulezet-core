from __future__ import annotations
import os
import re
import shlex
from typing import Any, Dict, List, Optional
from uuid import UUID

import yaml

from app.core.utils.utils import detect_cve
from app.features.rule.rule_core import get_rule
from app.features.rule.rule_format.abstract_rule_type.rule_type_abstract import (
    RuleType,
    ValidationResult,
)


####################
#   Plum class     #
####################

# Canonical `namespace:value` tag syntax — exact port of
# plum_antibodies/tag_validation.py's TAG_RE.
# https://github.com/D4-project/Plum-Antibodies/blob/main/documentation/tag-validation.md
_TAG_RE = re.compile(r"^[a-z][a-z0-9_-]*:[a-z0-9!._:/-]*$")

# Rule name: lowercase slug, max 25 chars (sanity-check.py NAME_RE).
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,24}$")

# version stamp: YYYYMMDDTHHMMSSZ (sanity-check.py VERSION_RE).
_VERSION_RE = re.compile(r"^\d{8}T\d{6}Z$")

_LINK_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)

_HTTP_HEADER_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9a-z]+$")

# Fields a Plum-Island search query may reference — sanity-check.py
# ALLOWED_FIELDS, see documentation/query-syntax.md and AGENT.md.
_ALLOWED_FIELDS = {
    "ip", "net", "fqdn", "fqdn_requested", "host", "domain", "domain_requested",
    "tld", "tag", "port", "http_title", "http_favicon_path", "http_favicon_mmhash",
    "http_favicon_md5", "http_favicon_sha256", "http_cookiename", "http_etag",
    "http_header", "http_headval", "http_server", "x509_issuer", "x509_issuer_cn",
    "x509_md5", "x509_sha1", "x509_sha256", "x509_subject", "x509_subject_cn",
    "x509_san", "banner",
}
_ALLOWED_MODIFIERS = {".lk", ".like", ".bg", ".begin", ".not", ".nt"}
_VALUE_MODIFIERS = {".lk", ".like", ".bg", ".begin"}
_EXACT_ONLY_FIELDS = {"tag"}


class _PlumQueryError(ValueError):
    """A `query` value does not follow Plum-Island's search syntax."""


class _PlumTagError(ValueError):
    """A `tags` entry does not follow the Plum-Antibodies tag contract."""


def _split_groups(query: str) -> List[List[str]]:
    """Split a Plum query into OR-separated AND-groups of tokens, exactly
    like sanity-check.py's split_groups(): implicit AND inside a group,
    explicit OR between groups, no group may start/end with OR."""
    try:
        parts = shlex.split(query)
    except ValueError as error:
        raise _PlumQueryError(f"invalid quoting: {error}") from error
    if not parts:
        raise _PlumQueryError("empty query")

    groups: List[List[str]] = []
    current: List[str] = []
    previous = None
    for part in parts:
        operator = part.upper()
        if operator == "OR":
            if not current:
                raise _PlumQueryError("OR cannot start, end, or follow another OR")
            groups.append(current)
            current = []
        elif operator == "AND":
            if not current or previous in {"AND", "OR"}:
                raise _PlumQueryError("AND must join two search terms")
        else:
            current.append(part)
        previous = operator

    if not current:
        raise _PlumQueryError("query cannot end with OR")
    groups.append(current)
    return groups


def _validate_http_headval(term: str) -> None:
    payload = term[len("http_headval:"):]
    if ":" not in payload:
        raise _PlumQueryError("http_headval requires header:value")
    header_expr, value = payload.split(":", 1)
    if not header_expr or not value.strip():
        raise _PlumQueryError("http_headval requires a non-empty header and value")
    for modifier in _VALUE_MODIFIERS:
        if header_expr.endswith(modifier):
            header_expr = header_expr[: -len(modifier)]
            break
    header_expr = header_expr.lower()
    if not _HTTP_HEADER_RE.fullmatch(header_expr) or len(header_expr) > 128:
        raise _PlumQueryError(f"invalid HTTP header name: {header_expr!r}")


def _validate_term(term: str, negated: bool = False) -> None:
    if term.lower().startswith("http_headval:"):
        _validate_http_headval(term)
        return
    if ":" not in term:
        raise _PlumQueryError(f"expected field:value, got {term!r}")

    key, value = term.split(":", 1)
    key = key.lower()
    if not value:
        raise _PlumQueryError(f"empty value for {key}")

    modifier = ""
    base = key
    for suffix in _ALLOWED_MODIFIERS:
        if key.endswith(suffix):
            modifier = suffix
            base = key[: -len(suffix)]
            break

    if base not in _ALLOWED_FIELDS:
        raise _PlumQueryError(f"unsupported search field: {base}")
    if modifier and base in _EXACT_ONLY_FIELDS:
        raise _PlumQueryError(f"{base} does not support {modifier}")
    if negated and modifier in {".not", ".nt"}:
        raise _PlumQueryError("NOT cannot be combined with .not or .nt")


def _validate_query(query: str) -> None:
    for group in _split_groups(query):
        positive_terms = []
        tokens = iter(group)
        for token in tokens:
            if token.upper() == "NOT":
                operand = next(tokens, None)
                if operand is None or operand.upper() in {"AND", "OR", "NOT"}:
                    raise _PlumQueryError("NOT must be followed by a field:value term")
                _validate_term(operand, negated=True)
            else:
                positive_terms.append(token)
                _validate_term(token)
        if not positive_terms:
            raise _PlumQueryError("each OR group containing NOT needs a positive term")


def _normalize_tag(raw_tag: Any) -> str:
    """Port of plum_antibodies.tag_validation.validate_tag(): strip,
    lowercase, reduce legacy `tag:namespace:value` input, then enforce
    `namespace:value` syntax with no whitespace."""
    if not isinstance(raw_tag, str):
        raise _PlumTagError("every tag must be a string")
    tag = raw_tag.strip().lower()
    while tag.startswith("tag:") and tag.count(":") >= 2:
        tag = tag.split(":", 1)[1].strip()
    if not _TAG_RE.fullmatch(tag):
        raise _PlumTagError(f"tag {raw_tag!r} must use namespace:value syntax with no whitespace")
    return tag


def _normalize_tags(raw_tags: Any) -> List[str]:
    """Port of plum_antibodies.tag_validation.validate_tags(): a
    non-empty list of tag strings, normalized and de-duplicated."""
    if not isinstance(raw_tags, list) or not raw_tags:
        raise _PlumTagError("tags must be a non-empty list of tag strings")
    tags: List[str] = []
    seen = set()
    for raw_tag in raw_tags:
        tag = _normalize_tag(raw_tag)
        if tag in seen:
            continue
        seen.add(tag)
        tags.append(tag)
    return tags


class PlumRule(RuleType):
    """
    Concrete implementation of RuleType for Plum-Antibodies rules: YAML
    host/service fingerprinting rules that match scanner data (HTTP
    headers, favicon hashes, banners, certificates) and apply normalized
    `namespace:value` tags such as `product:nginx` or `vendor:cisco`.

    Upstream: https://github.com/D4-project/Plum-Antibodies
    Format contract: documentation/tagging.md, documentation/query-syntax.md,
    documentation/tag-validation.md, documentation/sanity-check.md.
    """

    @property
    def format(self) -> str:
        return "plum"

    def get_class(self) -> str:
        return "PlumRule"

    ##############################
    #        FORMAT DETECT       #
    ##############################
    def detect(self, content: str) -> bool:
        """
        A top-level `query` string together with a top-level `uuid` and a
        `version` matching Plum's `YYYYMMDDTHHMMSSZ` stamp is a
        combination no other YAML-based format here uses (Sigma:
        `logsource`+`detection`; ATR: `agent_source`/`detection.conditions`;
        Splunk: `search`+`how_to_implement`+`known_false_positives`; Kunai:
        `matches`+`condition`) — none of them define a top-level `query`
        string field at all, so this disambiguates Plum on the shared
        .yml/.yaml extension without needing the full validate() pass.
        """
        try:
            doc = yaml.safe_load(content)
        except Exception:
            return False
        if not isinstance(doc, dict):
            return False
        version = doc.get("version")
        return (
            isinstance(doc.get("query"), str) and
            "uuid" in doc and
            isinstance(version, str) and bool(_VERSION_RE.match(version))
        )

    ##############################
    #         VALIDATION         #
    ##############################
    def validate(self, content: str, **kwargs) -> ValidationResult:
        """
        Faithful port of Plum-Antibodies' `tools/sanity-check.py`: required
        fields, a lowercase `name` slug, a canonical `uuid`, `query` syntax
        (allowed fields, value modifiers, AND/OR/NOT grouping), normalized
        `namespace:value` `tags`, optional HTTP(S) `references`, and the
        `YYYYMMDDTHHMMSSZ` `version` stamp.
        """
        try:
            doc = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            return ValidationResult(ok=False, errors=[f"YAML parse error: {exc}"], normalized_content=content)

        if not isinstance(doc, dict):
            return ValidationResult(ok=False, errors=["Empty or invalid YAML content."], normalized_content=content)

        errors: List[str] = []

        required = ("name", "description", "uuid", "query", "tags", "version")
        missing = [field for field in required if field not in doc]
        if missing:
            errors.append(f"Missing required field(s): {', '.join(missing)}")

        if "name" in doc:
            name = doc.get("name")
            if not isinstance(name, str) or not _NAME_RE.fullmatch(name):
                errors.append("name must be a lowercase slug of at most 25 characters (a-z, 0-9, -)")

        if "description" in doc:
            description = doc.get("description")
            if not isinstance(description, str) or not description.strip():
                errors.append("description must be a non-empty string")

        if "uuid" in doc:
            rule_uuid = doc.get("uuid")
            if not isinstance(rule_uuid, str):
                errors.append("uuid must be a canonical UUID string")
            else:
                try:
                    if str(UUID(rule_uuid)) != rule_uuid:
                        errors.append("uuid must be a canonical UUID string")
                except ValueError:
                    errors.append("uuid must be a canonical UUID string")

        if "query" in doc:
            query = doc.get("query")
            if not isinstance(query, str):
                errors.append("query must be a string")
            else:
                try:
                    _validate_query(query)
                except _PlumQueryError as exc:
                    errors.append(f"invalid query: {exc}")

        if "tags" in doc:
            try:
                _normalize_tags(doc.get("tags"))
            except _PlumTagError as exc:
                errors.append(str(exc))

        if "references" in doc:
            references = doc.get("references")
            if not isinstance(references, list) or not references:
                errors.append("references must be a YAML list of links")
            else:
                for reference in references:
                    if not isinstance(reference, str) or not _LINK_RE.fullmatch(reference.strip()):
                        errors.append(f"invalid reference link: {reference!r}")

        if "version" in doc:
            version = doc.get("version")
            if not isinstance(version, str) or not _VERSION_RE.fullmatch(version):
                errors.append("version must use YYYYMMDDTHHMMSSZ")

        return ValidationResult(ok=len(errors) == 0, errors=errors, normalized_content=content)

    ##############################
    #          METADATA          #
    ##############################
    def parse_metadata(
        self,
        content: str,
        info: Optional[Dict[str, Any]] = None,
        validation_result: Optional[ValidationResult] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        `name` is Plum's lowercase rule slug (e.g. "blackboard") and
        becomes the rule title; `description` ("Detect <product or
        vendor>") stays the human-readable detection statement. The
        canonical `uuid` field maps directly onto Rulezet's
        `original_uuid` — unlike Kunai's dotted name or ATR's textual
        identifier, Plum rules already carry a real UUID.
        """
        info = info or {}
        title_fallback = "Untitled Plum rule"
        try:
            doc = yaml.safe_load(content)
            if not isinstance(doc, dict):
                raise ValueError("Content is empty or not valid YAML.")

            name = doc.get("name", "untitled")
            description = doc.get("description") or f"Detect {name}"
            _, cve = detect_cve(description if isinstance(description, str) else "")

            try:
                tags_list = _normalize_tags(doc.get("tags"))
            except _PlumTagError:
                tags_list = [t for t in (doc.get("tags") or []) if isinstance(t, str)]

            return {
                "format": "plum",
                "title": name,
                "license": info.get("license", "AGPL-3.0"),
                "description": description,
                "version": str(doc.get("version", "N/A")),
                "author": info.get("author", "Plum-Antibodies Community"),
                "cve_id": cve,
                "original_uuid": doc.get("uuid") or name,
                "source": info.get("repo_url", "https://github.com/D4-project/Plum-Antibodies"),
                "to_string": (validation_result.normalized_content if validation_result else None) or content,
                "tags": tags_list,
                # Not a canonical Rule field elsewhere — kept for callers
                # that want the original rule slug (e.g. a future
                # rule_tester driver replaying scan fixtures against `query`).
                "plum_name": name,
            }
        except Exception as exc:
            return {
                "format": "plum",
                "title": title_fallback,
                "license": info.get("license", "AGPL-3.0"),
                "description": f"Error parsing metadata: {exc}",
                "version": "N/A",
                "author": info.get("author", "Plum-Antibodies Community"),
                "cve_id": [],
                "original_uuid": "Unknown",
                "source": info.get("repo_url", "https://github.com/D4-project/Plum-Antibodies"),
                "to_string": content,
            }

    ##############################
    #         EXTRACTION         #
    ##############################
    def get_rule_files(self, file: str) -> bool:
        """Return True if the file looks like a candidate Plum rule file by extension."""
        return file.endswith((".yml", ".yaml"))

    def extract_rules_from_file(self, filepath: str) -> List[str]:
        """
        Plum-Antibodies ships exactly one rule per YAML file (see
        upstream `tags/*.yaml`), but multi-document files are handled the
        same defensive way as the other YAML-based formats here. Each
        document is self-filtered through detect() since this can be
        called directly by find_rule_in_repo without the candidate/
        detect() disambiguation main_format.py/session_class.py apply
        first — irrelevant when the extension is unambiguous but needed
        for shared .yml/.yaml files.
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return []

        try:
            docs = list(yaml.safe_load_all(content))
        except Exception:
            return []

        rules = []
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            raw = yaml.dump(doc, sort_keys=False, allow_unicode=True)
            if self.detect(raw):
                rules.append(raw)
        return rules

    def _walk_yaml_files(self, repo_dir: str) -> List[str]:
        """Walk repo_dir for candidate Plum YAML files (mirrors atr_format/sigma_format)."""
        rule_files: List[str] = []
        if not os.path.exists(repo_dir):
            return rule_files
        for root, dirs, files in os.walk(repo_dir, followlinks=False):
            dirs[:] = [d for d in dirs if not d.startswith(".") and not d.startswith("_")
                       and not os.path.islink(os.path.join(root, d))]
            for fname in files:
                if fname.startswith(".") or fname.startswith("_"):
                    continue
                filepath = os.path.join(root, fname)
                # Reject symlinks — open() would otherwise follow one straight
                # to its target and leak arbitrary filesystem content as a "rule".
                if os.path.islink(filepath):
                    continue
                if fname.endswith((".yml", ".yaml")):
                    rule_files.append(filepath)
        return rule_files

    def find_rule_in_repo(self, repo_dir: str, rule_id: int) -> tuple[str, bool]:
        """Locate a previously-imported Plum rule's current text in a repo
        directory by its stable original_uuid (Plum's own canonical `uuid`)."""
        rule = get_rule(rule_id)
        if not rule:
            return "No rule found in the database.", False

        target_uuid = getattr(rule, "original_uuid", None)
        for filepath in self._walk_yaml_files(repo_dir):
            for raw in self.extract_rules_from_file(filepath):
                try:
                    doc = yaml.safe_load(raw)
                except Exception:
                    continue
                if not isinstance(doc, dict):
                    continue
                if target_uuid and doc.get("uuid") == target_uuid:
                    return raw, True

        return f"Plum rule '{target_uuid}' not found inside local repo.", False
