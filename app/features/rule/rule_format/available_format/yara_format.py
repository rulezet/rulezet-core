import os
from typing import Dict, Any, List, Optional
import re
import yara
from app.features.rule.rule_core import get_rule, _active
from app.features.rule.rule_format.abstract_rule_type.rule_type_abstract import RuleType, ValidationResult
from app.core.utils.utils import detect_cve
from app.core.db_class.db import Rule
from flask import current_app


#################
#   YARA class  #
#################


#
#   Implement the yara section with check all the abstract method.
#

#-----------------------------------------------#
#   Other method to help (add import ....)      #
#-----------------------------------------------#

def insert_import_module(rule_text, module_name):
    lines = rule_text.strip().splitlines()
    if not any(line.strip().startswith(f'import "{module_name}"') for line in lines):
        return f'import "{module_name}"\n' + rule_text
    return rule_text


# ref A6: a 'global rule' declaration has its condition implicitly ANDed
# into every other rule compiled in the same YARA namespace. It compiles
# fine on its own, so this can't be caught by syntax validation alone —
# it has to be flagged explicitly. Rulezet's own rule tester keeps users
# namespace-isolated when testing, but a rule downloaded and compiled
# elsewhere without namespacing is still exposed.
_GLOBAL_RULE_RE = re.compile(r'^\s*((?:private|global)\s+)+rule\b', re.MULTILINE | re.IGNORECASE)


def detect_global_rule_risk(content: str) -> dict:
    """
    Detect a 'global rule' declaration in YARA rule content.

    Returns {'flagged': bool, 'reasons': list[str]}.
    """
    for match in _GLOBAL_RULE_RE.finditer(content):
        if 'global' in match.group(1).lower():
            return {
                'flagged': True,
                'reasons': [
                    "Declares a 'global rule' — its condition is implicitly ANDed into "
                    "every other rule compiled in the same YARA namespace, so a "
                    "'global rule { condition: false }' can silently suppress every "
                    "other rule compiled alongside it outside of Rulezet's own "
                    "namespace-isolated execution."
                ],
            }
    return {'flagged': False, 'reasons': []}

def extract_undefined_identifier(error_msg: str) -> Optional[str]:
    """Pulls the identifier name out of a YARA 'undefined identifier "X"'
    compile error, e.g. what validate() itself matches against YARA_MODULES/
    ALLOWED_EXTERNALS above — used on the bad-rule edit page to go one step
    further for the case validate() *can't* auto-fix: X isn't a builtin
    module or external, it's another rule's name (YARA's cross-rule
    condition reference, e.g. `condition: Macho and ...`)."""
    match = re.search(r'undefined identifier "(\w+)"', error_msg or '')
    return match.group(1) if match else None


def find_missing_dependency_rule(var_name: str, bad_rule=None, source: str = None,
                                  github_path: str = None) -> Optional[Rule]:
    """Given an identifier YARA couldn't resolve on its own, look for an
    existing active YARA rule literally named var_name — the rule this one
    is meant to compile alongside. Returns None for anything validate()
    would already have auto-handled (a known module/external), since those
    never reach this far as a standing error.

    Multiple same-titled matches are disambiguated by preferring one from
    the same github_path, then the same source repo — the rule most likely
    to actually be the sibling this particular rule was extracted next to.
    `source`/`github_path` are the direct values when the caller already
    knows them (e.g. mid-import, from the repo it's currently walking);
    `bad_rule` is a convenience for the InvalidRuleModel case, read only
    when the explicit kwargs above aren't given.
    """
    if var_name in YaraRule.YARA_MODULES or var_name in allowed_externals():
        return None

    source = source or getattr(bad_rule, 'url', None)
    github_path = github_path or getattr(bad_rule, 'github_path', None)

    candidates = _active().filter(Rule.format == 'yara', Rule.title == var_name).all()
    if not candidates:
        candidates = _active().filter(
            Rule.format == 'yara', Rule.title.ilike(var_name)
        ).all()
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    if github_path:
        same_path = [c for c in candidates if c.github_path == github_path]
        if same_path:
            return same_path[0]

    if source:
        same_source = [c for c in candidates if c.source == source]
        if same_source:
            return same_source[0]

    return candidates[0]


def try_resolve_yara_missing_dependency(rule_instance, rule_text: str, metadata: dict,
                                         validation_result: ValidationResult, user,
                                         source_repo_url: str = None, github_path: str = None):
    """Second chance before a YARA rule that failed validate() becomes a
    bad_rule entry: if the failure is an undefined identifier that turns
    out to be another rule's name (YARA's cross-rule condition reference,
    e.g. `condition: Macho and ...`) already present on this instance,
    confirm it by compiling the two together, then import rule_text as-is
    (never the combined text) and record the dependency as an auto
    RuleRelation — same idea as the bad_rule edit page's "Link & recompile"
    action, just applied automatically at import time instead of waiting
    for a rule to fail first and a human to notice.

    Returns ('created', new_rule), ('skipped', None) — compiled fine
    together but add_rule_core rejected it (duplicate, dataset-collision
    guard, ...), the caller's normal duplicate handling applies, not a bad
    rule — or ('no_match', None) when nothing was resolved, meaning the
    caller should fall back to its own bad-rule handling as usual.
    """
    if rule_instance.format != 'yara' or validation_result.ok:
        return 'no_match', None

    var_name = extract_undefined_identifier('; '.join(validation_result.errors or []))
    if not var_name:
        return 'no_match', None

    target_rule = find_missing_dependency_rule(var_name, source=source_repo_url, github_path=github_path)
    if not target_rule:
        return 'no_match', None

    try:
        yara.compile(source=f"{target_rule.to_string or ''}\n\n{rule_text}")
    except Exception:
        return 'no_match', None

    from app.features.rule import rule_core as RuleModel
    from app.features.rule_relation.rule_relation_core import add_relation

    new_rule, _msg = RuleModel.add_rule_core(metadata, user)
    if not new_rule:
        return 'skipped', None

    add_relation(
        new_rule.id, target_rule.id, 'yara_condition_ref',
        note=f'Undefined identifier "{var_name}" resolved to this rule at import time',
        user_id=None, source='auto',
    )
    return 'created', new_rule


def allowed_externals() -> set:
    """YaraRule.ALLOWED_EXTERNALS plus any admin-configured
    YARA_ADDITIONAL_EXTERNAL identifiers (see .env_default) — read lazily,
    on every call, since current_app is only valid inside an active
    request/job app context, never at class-definition/import time. Doing
    this as a class-body-level `ALLOWED_EXTERNALS.update(current_app...)`
    instead raises RuntimeError("Working outside of application context")
    the moment this module is imported anywhere without one already pushed
    — e.g. tests/rules/test_yara_format.py imports YaraRule at module
    scope, before any fixture runs — and load_all_rule_formats() swallows
    that exception with just a print(), silently dropping the entire
    "yara" format from RuleType.__subclasses__() rather than crashing
    loudly.
    """
    try:
        extra = current_app.config.get('YARA_ADDITIONAL_EXTERNAL') or []
    except RuntimeError:
        extra = []
    return YaraRule.ALLOWED_EXTERNALS | set(extra)


class YaraRule(RuleType):
    @property
    def format(self) -> str:
        return "yara"

    YARA_MODULES = {"pe", "math", "cuckoo", "magic", "hash", "dotnet", "elf", "macho"}
    ALLOWED_EXTERNALS = {
        "filename", "filepath", "extension", "filetype",
        "md5", "sha1", "sha256", "owner", "new_file"
    }

    def get_class(self) -> str:
        return "YaraRule"

    # ---------------------#
    #   Abstract section  #
    # ---------------------#
    def validate(self, content: str, **kwargs) -> ValidationResult:
            ALLOWED_EXTERNALS = allowed_externals()

            externals = {}
            attempts = 0
            max_attempts = 10
            current_rule_text = content

            while attempts < max_attempts:
                try:
                    temp_compile_text = current_rule_text
                    
                    # def escape_internal_quotes(match):
                    #     prefix = match.group(1) 
                    #     content = match.group(2) 

                    #     escaped_content = content.replace('"', '\\"')
                    #     return f'{prefix}"{escaped_content}"'
                    # temp_compile_text = re.sub(r'(\$\w+\s*=\s*)"(.*)"', escape_internal_quotes, temp_compile_text)

                    yara.compile(source=temp_compile_text, externals=externals)

                    risk = detect_global_rule_risk(current_rule_text)
                    return ValidationResult(ok=True, errors=[], warnings=risk['reasons'],
                                             normalized_content=current_rule_text)

                except yara.SyntaxError as e:
                    error_msg = str(e)
                    match_id = re.search(r'undefined identifier "(\w+)"', error_msg)
                    
                    if match_id:
                        var_name = match_id.group(1)
                        
                        if var_name in self.YARA_MODULES:
                            current_rule_text = insert_import_module(current_rule_text, var_name)
                            attempts += 1
                            continue
                        
                        elif var_name in ALLOWED_EXTERNALS:
                            externals[var_name] = "dummy_value"
                            attempts += 1
                            continue
                    
                    return ValidationResult(ok=False, errors=[error_msg], normalized_content=current_rule_text)

                except Exception as e:
                    return ValidationResult(ok=False, errors=[str(e)], normalized_content=current_rule_text)

            return ValidationResult(ok=False, errors=["Max validation attempts exceeded"], normalized_content=current_rule_text)

    def parse_metadata(self, content: str, info: Dict, validation_result: ValidationResult) -> Dict[str, Any]:
        """Extract metadata and normalize it into a rule dict."""
        
        # --- 1. Extract rule name first (MUST be present for identification) ---
        rule_name_match = re.search(r'rule\s+(\w+)', content)
        rule_name = rule_name_match.group(1) if rule_name_match else "UNKNOWN_RULE_NAME"
        
        try:
            meta = {}

            source_content = validation_result.normalized_content if validation_result.normalized_content else content
            
            meta_block = re.search(r'meta\s*:\s*(.*?)\n\s*(?:strings|condition|private|global)\s*:', source_content, re.DOTALL | re.IGNORECASE)
            
            if meta_block:
                meta_content = meta_block.group(1)
                entries = re.findall(r'(\w+)\s*=\s*"(.*?)"', meta_content, re.DOTALL)
                for key, val in entries:
                    meta[key] = val
            
            # --- 3. Detect CVE in description ---
            description = meta.get("description") or f"Rule {rule_name} (No description metadata provided)."
            _, cve = detect_cve(description)

            rule_dict = {
                "format": "yara",
                "title": rule_name, 
                "license": meta.get("license") or info.get("license", "unknown"),
                "description": description,
                "source": info.get("repo_url") or meta.get("source") or "Unknown",
                "version": meta.get("version", "1.0"),
                "original_uuid": meta.get("id") or meta.get("uuid")  or "Unknown",
                "author": meta.get("author") or info.get("author", "Unknown"),
                "to_string": source_content, 
                "cve_id": cve
            }
            return rule_dict
            
        except Exception as e:
            
            return {
                "format": "yara",
                "title": rule_name, 
                "license": info.get("license", "unknown"),
                "description": f"Error parsing optional metadata in rule '{rule_name}': {e}",
                "version": "N/A",
                "source": info.get("repo_url", "Unknown"),
                "original_uuid": "Unknown",
                "author": info.get("author", "Unknown"),
                "cve_id": [],
                "to_string": content,
            }

    def documentation_signals(self, content: str) -> Dict[str, bool]:
        """YARA-specific documentation checklist, read from the meta{} block —
        same regex approach as parse_metadata() above."""
        meta = {}
        meta_block = re.search(r'meta\s*:\s*(.*?)\n\s*(?:strings|condition|private|global)\s*:', content, re.DOTALL | re.IGNORECASE)
        if meta_block:
            entries = re.findall(r'(\w+)\s*=\s*"(.*?)"', meta_block.group(1), re.DOTALL)
            for key, val in entries:
                meta[key] = val
        return {
            "has_date": bool(meta.get("date")),
            "has_reference": bool(meta.get("reference") or meta.get("reference_url")),
            "has_description": bool(meta.get("description")),
        }

    def get_rule_files(self, file: str) -> bool:
        if file.endswith(('.yar', '.yara')):
            return True
        return False

        
    def extract_rules_from_file(self, filepath: str) -> List[str]:
        """
        Extract YARA rules from a file.

        Features:
        - Ignores rules that are inside comments (// or /* */).
        - Correctly handles strings so that '}', //, /* */, or /.../ regex inside quotes
        are treated as part of the string, not as rule terminators or comments.
        - Tracks braces to determine rule boundaries.
        """
        rules = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Parsing state variables
            brace_level = 0                  # Track nesting of { }
            inside_string = False            # Whether we are inside a "..." or '...'
            inside_regex = False             # Whether we are inside a /.../ regex
            string_char = None               # Which quote character started the string
            inside_line_comment = False      # Whether we are inside a // comment
            inside_block_comment = False     # Whether we are inside a /* */ comment
            current_rule = []                # Buffer for the current rule
            in_rule = False                  # Whether we are currently parsing a rule
            escaped = False                  # Handle escape sequences like \" or \'

            i = 0
            while i < len(content):
                char = content[i]
                nxt = content[i + 1] if i + 1 < len(content) else ""

                # --- Handle string content ---
                if inside_string:
                    current_rule.append(char)

                    if not escaped and char == string_char:  # End of string
                        inside_string = False
                        string_char = None
                    elif char == "\\" and not escaped:       # Escape character
                        escaped = True
                    else:
                        escaped = False

                    i += 1
                    continue

                # --- Handle regex content ---
                if inside_regex:
                    current_rule.append(char)

                    if not escaped and char == "/":  # End of regex
                        inside_regex = False
                    elif char == "\\" and not escaped:  # Escape in regex
                        escaped = True
                    else:
                        escaped = False

                    i += 1
                    continue

                # --- Handle comments (only when not inside a string or regex) ---
                if not inside_line_comment and not inside_block_comment:
                    if char == "/" and nxt == "/":  # Start of line comment
                        inside_line_comment = True
                        i += 2
                        continue
                    if char == "/" and nxt == "*":  # Start of block comment
                        inside_block_comment = True
                        i += 2
                        continue

                if inside_line_comment:
                    if char == "\n":               # End of line comment
                        inside_line_comment = False
                    i += 1
                    continue

                if inside_block_comment:
                    if char == "*" and nxt == "/": # End of block comment
                        inside_block_comment = False
                        i += 2
                        continue
                    i += 1
                    continue

                # --- If not inside string, comment, or regex ---
                if char in ('"', "'"):             # Start of a string
                    inside_string = True
                    string_char = char
                    escaped = False
                    current_rule.append(char)
                    i += 1
                    continue

                # Detect start of a regex (only if it's not // or /*)
                if not inside_regex and char == "/" and nxt not in ("/", "*"):
                    inside_regex = True
                    escaped = False
                    current_rule.append(char)
                    i += 1
                    continue

                # Detect the beginning of a rule
                if not in_rule and content.startswith("rule", i):
                    in_rule = True
                    current_rule = []

                # Count braces only outside strings, comments, and regex
                if char == "{":
                    brace_level += 1
                elif char == "}":
                    brace_level -= 1

                # If we are inside a rule, accumulate its content
                if in_rule:
                    current_rule.append(char)
                    if brace_level == 0 and char == "}":  # Rule is complete
                        rule_text = "".join(current_rule).strip()
                        if rule_text:
                            rules.append(rule_text)
                        in_rule = False
                        current_rule = []

                i += 1

        except Exception as e:
            return []

        return rules

    def get_rule_files_update(self, repo_dir: str) -> List[str]:
        """Retrieve all YARA rule files from a repository."""
        yara_files = []
        for root, dirs, files in os.walk(repo_dir, followlinks=False):
            dirs[:] = [d for d in dirs if not d.startswith('.') and not d.startswith('_')
                       and not os.path.islink(os.path.join(root, d))]
            for file in files:
                if file.startswith('.') or file.startswith('_'):
                    continue
                filepath = os.path.join(root, file)
                # A symlinked "rule file" would have open() silently follow it
                # to its target — reject before it ever reaches extract_rules_from_file.
                if os.path.islink(filepath):
                    continue
                if file.endswith(('.yar', '.yara')):
                    yara_files.append(filepath)
        return yara_files
    def find_rule_in_repo(self, repo_url: str, rule_id: int) -> tuple[str, bool]:
        """
        Search for a YARA rule inside a locally cloned GitHub repo.
        Repo is stored at: Rules_Github/<owner>/<repo>
        If it already exists → run git pull to update it.
        """
        rule = get_rule(rule_id)
        if not rule:
            return "No rule found in the database.", False

        yara_files = self.get_rule_files_update(repo_url)




        for filepath in yara_files:
            rules = self.extract_rules_from_file(filepath)
            for r in rules:
                match = re.search(r'rule\s+(\w+)', r)
                if match and match.group(1) == rule.title:
                    return r, True

        return f"Yara Rule '{rule.title}' not found inside local repo.", False



  