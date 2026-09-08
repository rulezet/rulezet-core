import os
import tomllib
import re
from typing import Any, Dict, List, Optional

from app.core.utils.utils import detect_cve
from app.features.rule.rule_core import get_rule
from app.features.rule.rule_format.abstract_rule_type.rule_type_abstract import RuleType, ValidationResult

######################
#   Elastic class    #
######################

# Elastic Security detection rules — one TOML file per rule ([metadata] +
# [rule] sections), the query living unstructured in `rule.query` (EQL/KQL/
# Lucene/ES|QL/threshold/new_terms, or absent entirely for machine_learning
# rules). Modeled on the elastic/detection-rules repo's own rule schema, but
# hand-rolled rather than a full jsonschema import for the same reason as
# splunk_format.py/atr_format.py: the schema's dynamic catalogs (`tags`
# free-text taxonomy, `threat.tactic`/`technique` names) are Elastic's own
# evolving corpus, not part of the generic query-rule format — enforcing
# them here would reject legitimately-formed community rules that aren't in
# Elastic's own repo. Only the short, spec-fixed enums (language, severity)
# and the required identity/logic fields are hard errors; everything else
# (author, references, threat mapping, false_positives/note/setup) is a
# warning — same calibration as every other format in this folder.

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE,
)
_MITRE_TECH_RE = re.compile(r'^T\d{4}(\.\d{3})?$')
_MITRE_TACTIC_RE = re.compile(r'^TA\d{4}$')

_VALID_SEVERITIES = frozenset({'low', 'medium', 'high', 'critical'})
_VALID_LANGUAGES = frozenset({'eql', 'kql', 'lucene', 'esql', 'threshold', 'new_terms', 'ml', 'machine_learning'})
_QUERYLESS_TYPES = frozenset({'ml', 'machine_learning'})

# A rule file always has an [metadata] and/or [rule] TOML table header —
# distinguishes an Elastic detection rule from an unrelated .toml file
# (pyproject.toml, Cargo.toml, a CI config, ...) that could otherwise sit
# in the same repo and get scanned as a candidate.
_ELASTIC_SIGNALS = re.compile(
    r'^\s*\[rule\]\s*$|^\s*\[metadata\]\s*$'
    r'|rule_id\s*=\s*["\'][0-9a-f]{8}-[0-9a-f]{4}'
    r'|language\s*=\s*["\'](?:eql|kql|lucene|esql|threshold|new_terms)["\']',
    re.IGNORECASE | re.MULTILINE,
)


def _as_list(value: Any) -> list:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _join_authors(author: Any) -> str:
    authors = [a for a in _as_list(author) if isinstance(a, str) and a.strip()]
    return ", ".join(authors) if authors else "Unknown"


def _title_from_path(github_path: Optional[str]) -> Optional[str]:
    """Elastic's own repo names each file after a slug of its rule — used
    as a fallback identity source when [rule].name itself is missing, and
    as a secondary match key in find_rule_in_repo()."""
    if not github_path:
        return None
    stem = os.path.splitext(os.path.basename(github_path))[0]
    words = [w for w in re.split(r'[_\-]+', stem) if w]
    return " ".join(w.capitalize() for w in words) if words else None


class ElasticRule(RuleType):
    """
    Concrete implementation of RuleType for Elastic Security detection
    rules — TOML files with an EQL/KQL/Lucene/ES|QL/threshold/new_terms
    query in `rule.query` (absent for `type = "machine_learning"` rules).

    Upstream: https://github.com/elastic/detection-rules
    """

    @property
    def format(self) -> str:
        return "elastic"

    def get_class(self) -> str:
        return "ElasticRule"

    ##############################
    #        FORMAT DETECT       #
    ##############################
    def detect(self, content: str) -> bool:
        """
        Cheap text-level pre-filter, used both by extract_rules_from_file()
        (so an unrelated .toml sitting in the same repo — pyproject.toml,
        Cargo.toml, a CI config — doesn't get imported as a bad Elastic
        rule) and available for cross-format disambiguation, even though no
        other format in this folder currently claims .toml.
        """
        return bool(_ELASTIC_SIGNALS.search(content or ""))

    ##############################
    #         VALIDATION         #
    ##############################
    def validate(self, content: str, **kwargs) -> ValidationResult:
        """
        Validate an Elastic Security detection rule. Two layers:

          1. Syntactic — the content parses as TOML.
          2. Semantic — required identity/logic fields are present and the
             short, spec-fixed enums (language, severity) hold a valid
             value. Everything Elastic's own dynamic content catalog
             governs (tags, threat/tactic/technique names, analytic
             grouping) is a warning, not a hard failure — see the module
             docstring.

        Does not re-dump TOML — returns the original content verbatim in
        `normalized_content` so quoting/ordering/comments are preserved.
        """
        try:
            doc = tomllib.loads(content)
        except Exception as exc:
            return ValidationResult(ok=False, errors=[f"TOML parse error: {exc}"], normalized_content=content)

        if not isinstance(doc, dict) or not doc:
            return ValidationResult(
                ok=False,
                errors=["Empty or invalid TOML content."],
                normalized_content=content,
            )

        errors: List[str] = []
        warnings: List[str] = []

        rule = doc.get("rule")
        if not isinstance(rule, dict):
            return ValidationResult(ok=False, errors=["Missing required [rule] section."], normalized_content=content)

        name = rule.get("name")
        if not isinstance(name, str) or not name.strip():
            errors.append("Missing or empty required field: rule.name")

        rule_id = rule.get("rule_id")
        if not isinstance(rule_id, str) or not rule_id.strip():
            errors.append("Missing required field: rule.rule_id")
        elif not _UUID_RE.match(rule_id.strip()):
            errors.append(f"rule.rule_id must be a valid UUID, got: {rule_id!r}")

        description = rule.get("description")
        if not isinstance(description, str) or not description.strip():
            errors.append("Missing or empty required field: rule.description")

        language = rule.get("language")
        if not isinstance(language, str) or language.lower() not in _VALID_LANGUAGES:
            errors.append(f"rule.language '{language}' is not one of: {sorted(_VALID_LANGUAGES)}")

        rule_type = (rule.get("type") or "").lower()
        query = rule.get("query")
        if rule_type not in _QUERYLESS_TYPES:
            if not isinstance(query, str) or not query.strip():
                errors.append("Missing or empty required field: rule.query (only machine_learning-type rules may omit it)")

        severity = rule.get("severity")
        if not isinstance(severity, str) or severity.lower() not in _VALID_SEVERITIES:
            errors.append(f"rule.severity '{severity}' is not one of: {sorted(_VALID_SEVERITIES)}")

        risk_score = rule.get("risk_score")
        if risk_score is None:
            errors.append("Missing required field: rule.risk_score")
        else:
            try:
                if not 0 <= int(risk_score) <= 100:
                    errors.append(f"rule.risk_score must be 0-100, got: {risk_score}")
            except (TypeError, ValueError):
                errors.append(f"rule.risk_score must be an integer, got: {risk_score!r}")

        if not rule.get("author"):
            warnings.append("Missing rule.author.")
        if not rule.get("references"):
            warnings.append("Missing rule.references.")

        threat = rule.get("threat")
        if not isinstance(threat, list) or not threat:
            warnings.append("Missing or empty rule.threat — used upstream to map this rule to MITRE ATT&CK.")
        else:
            for entry in threat:
                if not isinstance(entry, dict):
                    continue
                for tech in entry.get("technique") or []:
                    if not isinstance(tech, dict):
                        continue
                    tid = tech.get("id")
                    if tid and not _MITRE_TECH_RE.match(str(tid)):
                        warnings.append(f"threat.technique.id '{tid}' doesn't look like an ATT&CK technique ID (e.g. T1059.001).")
                    for sub in tech.get("subtechnique") or []:
                        sid = isinstance(sub, dict) and sub.get("id")
                        if sid and not _MITRE_TECH_RE.match(str(sid)):
                            warnings.append(f"threat.technique.subtechnique.id '{sid}' doesn't look like an ATT&CK sub-technique ID.")
                tactic = entry.get("tactic")
                tac_id = isinstance(tactic, dict) and tactic.get("id")
                if tac_id and not _MITRE_TACTIC_RE.match(str(tac_id)):
                    warnings.append(f"threat.tactic.id '{tac_id}' doesn't look like an ATT&CK tactic ID (e.g. TA0011).")

        for field_name in ("false_positives", "note", "setup"):
            if not rule.get(field_name):
                warnings.append(f"Missing recommended field: rule.{field_name}")

        return ValidationResult(ok=(len(errors) == 0), errors=errors, warnings=warnings, normalized_content=content)

    ##############################
    #       META PARSING         #
    ##############################
    def parse_metadata(self, content: str, info: Optional[Dict[str, Any]] = None,
                        validation_result: Optional[ValidationResult] = None, **kwargs) -> Dict[str, Any]:
        """
        Extract rulezet-canonical metadata from an Elastic detection rule.
        Never re-dumps TOML → preserves original formatting.
        """
        info = info or {}
        title_fallback = _title_from_path(info.get("github_path")) or "Untitled Elastic Rule"
        try:
            doc = tomllib.loads(content)
            if not isinstance(doc, dict) or not doc:
                raise ValueError("Empty or non-mapping TOML")

            rule = doc.get("rule") or {}
            meta = doc.get("metadata") or {}

            title = (rule.get("name") or "").strip() or title_fallback
            description = rule.get("description", "No description provided")
            severity = (rule.get("severity") or "unknown").strip().lower()
            if severity not in _VALID_SEVERITIES:
                severity = "unknown"

            _, cve_ids = detect_cve(description if isinstance(description, str) else "")

            # threat.technique(.subtechnique).id — MITRE ATT&CK mapping.
            mitre_ids: List[str] = []
            for entry in rule.get("threat") or []:
                if not isinstance(entry, dict):
                    continue
                for tech in entry.get("technique") or []:
                    if not isinstance(tech, dict):
                        continue
                    if tech.get("id"):
                        mitre_ids.append(str(tech["id"]))
                    for sub in tech.get("subtechnique") or []:
                        if isinstance(sub, dict) and sub.get("id"):
                            mitre_ids.append(str(sub["id"]))

            # Elastic's own `tags` array is already a well-formed, human-
            # readable free-text taxonomy (e.g. "OS: Windows",
            # "Tactic: Collection", "Data Source: Elastic Defend") — pass
            # it through directly rather than reinventing prefixed tags,
            # same convention as every other format's tags flattening.
            tags_list = [t for t in (rule.get("tags") or []) if isinstance(t, str)] + mitre_ids

            return {
                "title": title,
                "format": "elastic",
                "license": rule.get("license") or info.get("license", "Unknown"),
                "description": description,
                # Newer Elastic rules track history via git instead of an
                # explicit version field — updated_date is a date, not a
                # version number, so it's kept out of this fallback chain.
                "version": str(rule.get("version") or "1.0"),
                "author": _join_authors(rule.get("author")) or info.get("author", "Unknown"),
                "cve_id": cve_ids,
                "original_uuid": rule.get("rule_id") or "Unknown",
                "source": info.get("repo_url", "Unknown"),
                "severity": severity,
                "tags": tags_list,
                "to_string": content,
            }

        except Exception as exc:
            return {
                "format": "elastic",
                "title": f"{title_fallback} (Metadata Error)",
                "license": info.get("license", "Unknown"),
                "description": f"Error parsing metadata: {exc}",
                "version": "N/A",
                "source": info.get("repo_url", "Unknown"),
                "original_uuid": "Unknown",
                "author": info.get("author", "Unknown"),
                "cve_id": [],
                "severity": "unknown",
                "tags": [],
                "to_string": content,
            }

    ##############################
    #     DOCUMENTATION SIGNALS  #
    ##############################
    def documentation_signals(self, content: str) -> Dict[str, bool]:
        """Elastic-specific documentation checklist, straight from the
        format's optional-but-conventional fields."""
        try:
            doc = tomllib.loads(content)
        except Exception:
            return {}
        rule = doc.get("rule") if isinstance(doc, dict) else None
        if not isinstance(rule, dict):
            return {}
        return {
            "documents_references": isinstance(rule.get("references"), list) and len(rule.get("references")) > 0,
            "documents_false_positives": bool(rule.get("false_positives")),
            "documents_investigation_guide": bool((rule.get("note") or "").strip()) if isinstance(rule.get("note"), str) else False,
            "documents_setup": bool((rule.get("setup") or "").strip()) if isinstance(rule.get("setup"), str) else False,
            "documents_attack_mapping": isinstance(rule.get("threat"), list) and len(rule.get("threat")) > 0,
        }

    ##############################
    #         FILE LISTING       #
    ##############################
    def get_rule_files(self, file: str) -> bool:
        return file.endswith(".toml")

    ##############################
    #         EXTRACTION         #
    ##############################
    def extract_rules_from_file(self, filepath: str) -> List[str]:
        """
        Extract an Elastic detection rule from a TOML file. Unlike YAML-
        based formats, Elastic Security ships exactly one rule per file —
        no multi-document/list-of-rules shape to handle. Self-filters
        through detect() (same as splunk_format.py/atr_format.py) so an
        unrelated .toml (pyproject.toml, Cargo.toml, CI config) sitting in
        the same repo isn't reported as a bad Elastic rule.
        """
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return []

        return [content] if self.detect(content) else []

    ##############################
    #      SEARCH IN REPO        #
    ##############################
    def get_rule_files_update(self, repo_dir: str) -> List[str]:
        rule_files = []
        if not os.path.exists(repo_dir):
            return rule_files
        for root, dirs, files in os.walk(repo_dir, followlinks=False):
            dirs[:] = [d for d in dirs if not d.startswith('.') and not d.startswith('_')
                       and not os.path.islink(os.path.join(root, d))]
            for file in files:
                if file.startswith('.') or file.startswith('_'):
                    continue
                filepath = os.path.join(root, file)
                if os.path.islink(filepath):
                    continue
                if file.endswith('.toml'):
                    rule_files.append(filepath)
        return rule_files

    def find_rule_in_repo(self, repo_dir: str, rule_id: int) -> tuple[str, bool]:
        """
        Return the EXACT TOML rule from the repo without modifying anything.
        Matches by rule_id (Elastic's own UUID, stored as original_uuid) —
        the authoritative key — falling back to a title/filename match for
        a rule imported before original_uuid was captured.
        """
        rule = get_rule(rule_id)
        if not rule:
            return "No rule found in the database.", False

        elastic_files = self.get_rule_files_update(repo_dir)

        title_fallback_match = None
        for path in elastic_files:
            rules = self.extract_rules_from_file(path)
            for raw in rules:
                try:
                    doc = tomllib.loads(raw)
                    r = doc.get("rule") or {}
                    if rule.original_uuid and r.get("rule_id") == rule.original_uuid:
                        return raw, True
                    if r.get("name") == rule.title:
                        title_fallback_match = raw
                    elif _title_from_path(path) == rule.title:
                        title_fallback_match = raw
                except Exception:
                    continue

        if title_fallback_match is not None:
            return title_fallback_match, True

        return f"Elastic rule '{rule.title}' not found inside local repo.", False
