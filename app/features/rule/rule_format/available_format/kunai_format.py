import os
import re
from typing import Any, Dict, List

import yaml

from app.features.rule.rule_core import get_rule
from app.features.rule.rule_format.abstract_rule_type.rule_type_abstract import RuleType, ValidationResult
from app.core.utils.utils import detect_cve

##################
#   Kunai class  #
##################

# Kunai rule types (see https://why.kunai.rocks/docs/next/advanced/rule_syntax_reference).
_KUNAI_TYPES = {'dependency', 'detection', 'filter'}

# Explicit rule-to-rule composition reference: matches: { $shared: rule(other.rule.name) }
# — a rule depends on / reuses another rule's result by name. This is the
# real Kunai relation mechanism (dependency/detection/filter composition);
# there is no implicit relation between rules just because they sit in the
# same `---`-separated YAML document stream (a `---`-separated file is
# just "one rule after another", the way many other YAML formats list a
# batch of independent rules in one file — no relation implied by that
# alone).
_RULE_REF_RE = re.compile(r'rule\(\s*([\w.\-]+)\s*\)')


class KunaiRule(RuleType):
    """
    Concrete implementation of RuleType for Kunai (YAML-based EDR) rules.
    Sources: https://github.com/kunai-project/community-rules,
             https://github.com/digisquad-repo/kunai-rules

    Real-world Kunai rules are usually saved with a `.kun` extension but
    are plain YAML underneath — same content shape whether the file is
    named *.kun, *.yml, or *.yaml. *.kun is unambiguous (no other format
    here uses it) but *.yml/*.yaml collide with Sigma/ATR/Splunk, so
    detect() still has to disambiguate for those two extensions the same
    way those formats already do for each other.
    """

    @property
    def format(self) -> str:
        return "kunai"

    def get_class(self) -> str:
        return "KunaiRule"

    ##############################
    #        DISAMBIGUATION      #
    ##############################
    def detect(self, content: str) -> bool:
        """A top-level `matches` mapping + a top-level `condition` is the
        combination none of the other YAML-based formats use (Sigma:
        `logsource`+`detection`; ATR: `agent_source`/`detection.conditions`;
        Splunk: `search`+`how_to_implement`+`known_false_positives`).
        Deliberately does NOT require `match-on` or `meta` — a `type:
        dependency` rule (shared logic reused by other rules via
        `rule(name)`) legitimately has neither, only `name`/`matches`/
        `condition`. A `type` field, when present, is a strong extra
        signal since its value comes from a small closed Kunai-specific
        vocabulary."""
        try:
            doc = yaml.safe_load(content)
        except Exception:
            return False
        if not isinstance(doc, dict):
            return False

        if isinstance(doc.get('type'), str) and doc['type'] in _KUNAI_TYPES:
            return True

        return isinstance(doc.get('matches'), dict) and 'condition' in doc

    ##############################
    #        VALIDATION          #
    ##############################
    def validate(self, content: str, **kwargs) -> ValidationResult:
        try:
            doc = yaml.safe_load(content)
        except yaml.YAMLError as e:
            return ValidationResult(ok=False, errors=[f"YAML parse error: {e}"], normalized_content=content)

        if not isinstance(doc, dict):
            return ValidationResult(ok=False, errors=["Empty or invalid YAML content."], normalized_content=content)

        # 'meta' and 'match-on' are both optional — a type: dependency rule
        # (pure shared logic, reused by other rules via rule(name)) has
        # neither; only detection/filter rules bind to actual kunai events
        # via match-on.
        required = ['name', 'matches', 'condition']
        missing = [k for k in required if k not in doc]
        if missing:
            return ValidationResult(ok=False, errors=[f"Missing required field(s): {', '.join(missing)}"],
                                     normalized_content=content)

        rule_type = doc.get('type')
        if rule_type is not None and rule_type not in _KUNAI_TYPES:
            return ValidationResult(ok=False, errors=[f"Unknown rule type '{rule_type}' — expected one of {sorted(_KUNAI_TYPES)}"],
                                     normalized_content=content)

        return ValidationResult(ok=True, normalized_content=content)

    ##############################
    #          METADATA          #
    ##############################
    def parse_metadata(self, content: str, info: Dict, validation_result: ValidationResult) -> Dict[str, Any]:
        """`name` is the closest thing Kunai has to a stable identifier
        (dotted, e.g. "kill.critical.service") — used as both title and
        original_uuid, the same way Wazuh uses its numeric <rule id> for
        both identity and display."""
        name = "Untitled"
        try:
            doc = yaml.safe_load(content)
            if not isinstance(doc, dict):
                raise ValueError("Content is empty or not valid YAML.")

            name = doc.get('name', 'Untitled')
            meta = doc.get('meta') or {}
            authors = meta.get('authors') or []
            comments = meta.get('comments') or []
            rule_type = doc.get('type')
            description = ' — '.join(str(c) for c in comments) if comments else f"Kunai rule '{name}'"
            _, cve = detect_cve(description)

            return {
                "format": "kunai",
                "title": name,
                "license": info.get("license", "unknown"),
                "description": description,
                "version": str(meta.get('version', '1.0')),
                "author": ', '.join(str(a) for a in authors) if authors else info.get("author", "Unknown"),
                "cve_id": cve,
                "original_uuid": name,
                "source": info.get("repo_url", ""),
                "to_string": validation_result.normalized_content or content,
                # Not a canonical Rule field elsewhere — kept for callers
                # that want to distinguish detection/filter/dependency
                # rules (e.g. a future rule_tester driver); harmless extra
                # key for callers that don't care.
                "kunai_rule_type": rule_type,
            }
        except Exception as e:
            return {
                "format": "kunai",
                "title": name,
                "license": info.get("license", "unknown"),
                "description": f"Error parsing metadata for rule '{name}': {e}",
                "version": "N/A",
                "author": info.get("author", "Unknown"),
                "cve_id": [],
                "original_uuid": name,
                "source": info.get("repo_url", ""),
                "to_string": content,
            }

    ##############################
    #        RELATIONS           #
    ##############################
    def extract_relations(self, content: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """The real Kunai composition mechanism: a `matches:` entry can be
        `rule(<name>)` instead of a raw condition, meaning "reuse that
        other rule's result here" — see the "Rule Composition Strategy"
        section of https://why.kunai.rocks/docs/next/advanced/rule_syntax_reference
        (dependency rules holding shared logic, detection rules composing
        other detection/filter rules for false-positive exclusion, etc).
        This is an explicit, directional reference by rule name — resolved
        as a target_ref against the referenced rule's `name` (=
        original_uuid), same as Wazuh's if_sid.

        NOT a relation source: two rules merely sitting in the same
        `---`-separated YAML document stream. That's just "a file listing
        several rules one after another", the same as any other
        multi-document YAML rule file — no relation is implied by
        proximity alone.
        """
        try:
            doc = yaml.safe_load(content)
        except Exception:
            return []
        if not isinstance(doc, dict):
            return []

        matches = doc.get('matches')
        if not isinstance(matches, dict):
            return []

        relations = []
        seen = set()
        for expr in matches.values():
            if not isinstance(expr, str):
                continue
            for target_name in _RULE_REF_RE.findall(expr):
                if target_name in seen:
                    continue
                seen.add(target_name)
                relations.append({
                    'kind': 'target_ref',
                    'target_identifier': target_name,
                    'relation_type': 'rule_ref',
                })
        return relations

    ##############################
    #         EXTRACTION         #
    ##############################
    def get_rule_files(self, file: str) -> bool:
        return file.endswith(('.kun', '.yml', '.yaml'))

    def extract_rules_from_file(self, filepath: str) -> List[str]:
        """Kunai rule files can hold several `---`-separated YAML documents
        — just a batch of independent rules listed one after another (no
        relation implied by that alone, see extract_relations). safe_load
        only ever returns the LAST document in a `---`-separated stream,
        so this needs safe_load_all, unlike Sigma's single-dict-or-plain-
        list handling. Self-filters each document through detect() for the
        same reason Sigma's extract_rules_from_file does (this can be
        called directly by find_rule_in_repo without the candidate/
        detect() disambiguation main_format.py/session_class.py apply
        first) — irrelevant for a .kun file (nothing else claims that
        extension) but still needed for .yml/.yaml."""
        rules = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            for doc in yaml.safe_load_all(content):
                if not isinstance(doc, dict):
                    continue
                raw = yaml.dump(doc, sort_keys=False, allow_unicode=True)
                if self.detect(raw):
                    rules.append(raw)
        except Exception:
            return []
        return rules

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
                if file.endswith(('.kun', '.yml', '.yaml')):
                    rule_files.append(filepath)
        return rule_files

    def find_rule_in_repo(self, repo_dir: str, rule_id: int) -> tuple[str, bool]:
        rule = get_rule(rule_id)
        if not rule:
            return "No rule found in the database.", False

        for filepath in self.get_rule_files_update(repo_dir):
            for raw in self.extract_rules_from_file(filepath):
                try:
                    parsed = yaml.safe_load(raw)
                    if not parsed or not isinstance(parsed, dict):
                        continue
                    if parsed.get("name") == rule.original_uuid:
                        return raw, True
                except Exception:
                    continue

        return f"Kunai rule '{rule.original_uuid}' not found inside local repo.", False
