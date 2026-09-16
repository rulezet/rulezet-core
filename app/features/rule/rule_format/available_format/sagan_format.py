import os
from typing import List, Dict, Any

from suricataparser import parse_rules

from app.features.rule.rule_core import get_rule
from app.features.rule.rule_format.abstract_rule_type.rule_type_abstract import RuleType, ValidationResult
from app.core.utils.utils import detect_cve
from app.features.rule.rule_format.available_format._snort_family_common import (
    SURICATA_PROTOCOLS, SAGAN_ONLY_PROTOCOLS, looks_like_sagan, extract_msg_sid_rev,
)


class SaganRule(RuleType):
    """
    Concrete implementation of RuleType for Sagan rules
    (https://github.com/quadrantsec/sagan-rules).

    Sagan matches log lines rather than network packets and shares its
    header/option grammar with Suricata/Snort, so it parses fine with the
    same `suricataparser` grammar-only parser — see
    docs/design/suricata_sagan_rework.md (issue #61) for why these two
    formats need to be told apart explicitly rather than lumped together.
    """

    @property
    def format(self) -> str:
        return "sagan"

    def get_class(self) -> str:
        return "SaganRule"

    def detect(self, content: str) -> bool:
        """Positive identification for the ambiguous-extension disambiguation
        (both formats claim .rule/.rules) — mirrors SuricataRule.detect()'s
        negation of the same check."""
        return looks_like_sagan(content)

    def validate(self, content: str, **kwargs) -> ValidationResult:
        """
        Validate Sagan rules. Grammar is shared with Suricata
        (suricataparser); the only thing to check here is the protocol,
        which Sagan allows as Suricata's real set PLUS 'any'/'syslog' (a
        superset, not a swap — some real Sagan rules do use tcp/udp).
        Sagan's own option keywords (program:, parse_src_ip:, ...) aren't
        checked against an allowlist here because nothing in this format
        needs to reject them — that's Suricata's job when a rule using
        them is mistagged as suricata, not Sagan's when they're used
        correctly.
        """
        try:
            rules = parse_rules(content)
            if not rules:
                return ValidationResult(ok=False, errors=["No valid Sagan rules found."], normalized_content=content)

            allowed_protocols = SURICATA_PROTOCOLS | SAGAN_ONLY_PROTOCOLS
            for rule in rules:
                header_parts = (rule.header or '').split()
                protocol = header_parts[0].lower() if header_parts else None
                if protocol and protocol not in allowed_protocols:
                    return ValidationResult(
                        ok=False,
                        errors=[f'protocol "{protocol}" is not a valid Sagan/Suricata protocol.'],
                        normalized_content=content,
                    )

            return ValidationResult(
                ok=True,
                warnings=[],
                normalized_content="\n".join([rule.raw for rule in rules]),
            )
        except Exception as e:
            return ValidationResult(ok=False, errors=[str(e)], normalized_content=content)

    def parse_metadata(self, content: str, info: Dict, validation_result: ValidationResult) -> Dict[str, Any]:
        """Extract metadata from a Sagan rule string — same msg/sid/rev
        shape as Suricata's, via the shared helper."""
        source_content = validation_result.normalized_content if validation_result.normalized_content else content
        msg, sid, rev = extract_msg_sid_rev(source_content)

        title = msg or "Untitled Sagan Rule"
        _, cve = detect_cve(title)

        return {
            "format": "sagan",
            "title": title,
            "license": info.get("license", "unknown"),
            "description": info.get("description", "No description provided"),
            "version": rev or "1",
            "author": info.get("author", "Unknown"),
            "cve_id": cve,
            "original_uuid": sid or "Unknown",
            "source": info.get("repo_url", "Unknown"),
            "to_string": content,
        }

    def documentation_signals(self, content: str) -> Dict[str, bool]:
        """Same regex approach as Suricata's own documentation_signals()."""
        import re
        return {
            "has_reference": bool(re.search(r'\breference\s*:', content)),
            "has_classtype": bool(re.search(r'\bclasstype\s*:', content)),
            "has_metadata": bool(re.search(r'\bmetadata\s*:', content)),
        }

    def get_rule_files(self, file: str) -> bool:
        return file.endswith(('.rule', '.rules'))

    def extract_rules_from_file(self, filepath: str) -> List[str]:
        """Extract raw Sagan rules from a file, skipping empty lines."""
        rules = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                parsed_rules = parse_rules(content)
                for rule in parsed_rules:
                    if rule.raw:
                        rules.append(rule.raw.strip())
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
                if not file.startswith('.') and not file.startswith('_'):
                    filepath = os.path.join(root, file)
                    if os.path.islink(filepath):
                        continue
                    if self.get_rule_files(file):
                        rule_files.append(filepath)
        return rule_files

    def find_rule_in_repo(self, repo_dir: str, rule_id: int) -> tuple[str, bool]:
        """Search for a Sagan rule by its original SID inside the repo."""
        rule_db = get_rule(rule_id)
        if not rule_db:
            return "No rule found in the database.", False

        rule_files = self.get_rule_files_update(repo_dir)

        for filepath in rule_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                    parsed_rules = parse_rules(content)
                    for parsed_rule in parsed_rules:
                        if str(parsed_rule.sid) == str(rule_db.original_uuid):
                            return parsed_rule.raw, True
            except Exception:
                continue

        return f"Sagan rule with SID '{rule_db.original_uuid}' not found.", False
