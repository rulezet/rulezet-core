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


def find_trusted_dependency_rule(var_name: str, rule_id: int = None, source: str = None,
                                 github_path: str = None, owner_ids=()) -> Optional[Rule]:
    """The rule an undefined identifier should be compiled with — only if
    it can be trusted to be the intended sibling, never just "some rule with
    that name": anyone can publish a rule named like a common identifier, and
    whatever gets picked here ends up compiled into other people's rules and
    in their "download with dependencies" files.

    Trusted, in this order: same GitHub path, same source (repository), an
    existing link from `rule_id` (e.g. a hand-made "depends on"), then a
    rule owned by one of `owner_ids` (the author / the person editing).
    A candidate declaring a `global` rule is never used — it would silently
    apply to every rule it is compiled with."""
    if var_name in YaraRule.YARA_MODULES or var_name in allowed_externals():
        return None
    candidates = _active().filter(Rule.format == 'yara', Rule.title == var_name).all() \
        or _active().filter(Rule.format == 'yara', Rule.title.ilike(var_name)).all()
    candidates = [c for c in candidates if c.id != rule_id and not detect_global_rule_risk(c.to_string or '')['flagged']]
    if not candidates:
        return None

    if github_path:
        hit = next((c for c in candidates if c.github_path == github_path), None)
        if hit:
            return hit
    if source:
        hit = next((c for c in candidates if c.source == source), None)
        if hit:
            return hit
    if rule_id:
        from app.core.db_class.db import RuleRelation
        linked = {tid for (tid,) in RuleRelation.query.filter_by(source_rule_id=rule_id)
                  .with_entities(RuleRelation.target_rule_id)}
        hit = next((c for c in candidates if c.id in linked), None)
        if hit:
            return hit
    owners = {o for o in owner_ids if o}
    if owners:
        hit = next((c for c in candidates if c.user_id in owners), None)
        if hit:
            return hit
    return None


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

    target_rule = find_trusted_dependency_rule(var_name, source=source_repo_url, github_path=github_path,
                                               owner_ids=(getattr(user, 'id', None),))
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


_CONDITION_RE = re.compile(r'\bcondition\s*:(.*?)(?=\n\s*}\s*(?:\n|$)|\Z)', re.S)
_COMMENT_OR_STRING_RE = re.compile(r'"(?:\\.|[^"\\\n])*"|/\*.*?\*/|//[^\n]*', re.S)


def _condition_references(text: str, rule_name: str) -> bool:
    """Whether one of the conditions in `text` uses `rule_name` as an
    identifier (strings and comments ignored)."""
    pattern = re.compile(rf'(?<![\w$#@!.]){re.escape(rule_name)}\b')
    for cond in _CONDITION_RE.findall(text or ''):
        if pattern.search(_COMMENT_OR_STRING_RE.sub(' ', cond)):
            return True
    return False


def sync_yara_dependency_relations(rule) -> int:
    """Record, as auto `yara_condition_ref` relations, which rule needs which
    in the chain a YARA rule compiles with (validate()'s `dependencies`):
    the rule itself -> the rules its condition names, and each of those ->
    the ones *its* condition names. Idempotent (add_relation skips existing
    links). Once the rule compiles, its own auto links to rules it no longer
    references (an edit removed the reference) are dropped. Returns how many
    links the chain has."""
    if (getattr(rule, 'format', '') or '').lower() != 'yara' or not rule.to_string:
        return 0
    result = YaraRule().validate(rule.to_string, rule_id=rule.id,
                                 source=getattr(rule, 'source', None),
                                 github_path=getattr(rule, 'github_path', None),
                                 owner_ids=(rule.user_id,))
    if result.ok:
        _prune_stale_yara_links(rule, result.dependencies)
    if not result.dependencies:
        return 0
    from app.features.rule_relation.rule_relation_core import add_relation
    chain = [rule] + list(result.dependencies)
    links = 0
    for src in chain:
        for dep in result.dependencies:
            if dep.id != src.id and _condition_references(src.to_string, dep.title):
                add_relation(src.id, dep.id, 'yara_condition_ref',
                             note=f'Condition references rule "{dep.title}"', user_id=None, source='auto')
                links += 1
    return links


def _prune_stale_yara_links(rule, dependencies) -> int:
    """Drop the rule's own auto `yara_condition_ref` links whose target it no
    longer references. Only auto links of that type — never a hand-made one."""
    from app import db
    from app.core.db_class.db import RuleRelation
    still = {d.id for d in dependencies if _condition_references(rule.to_string, d.title)}
    stale = (RuleRelation.query.filter_by(source_rule_id=rule.id, relation_type='yara_condition_ref', source='auto')
             .filter(RuleRelation.target_rule_id.notin_(still or {-1})).all())
    for rel in stale:
        db.session.delete(rel)
    if stale:
        db.session.commit()
    return len(stale)


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
    # A rule referencing others by name (`condition: Macho and ...`) only
    # compiles together with them — and they may reference others in turn.
    MAX_DEPENDENCIES = 50

    def validate(self, content: str, **kwargs) -> ValidationResult:
        """Compile the rule. Missing modules get their import added,
        allowed externals a dummy value, and an undefined identifier that is
        another rule's name is resolved to that rule — recursively (the rule
        it needs may need another one…) — and compiled together with it.

        Only the rule's own text is ever returned as normalized_content;
        the rules it needs come back in `dependencies`, in declaration order.

        kwargs:
            resolve_dependencies (bool, default True)
            rule_id (int)  — the rule being validated, never its own dependency
            source, github_path — to pick the right sibling among same-named rules
            owner_ids — rules of these users count as trusted dependencies
                        (default: the logged-in user) — see find_trusted_dependency_rule
        """
        ALLOWED_EXTERNALS = allowed_externals()
        resolve = kwargs.get('resolve_dependencies', True)
        self_id = kwargs.get('rule_id')
        owner_ids = kwargs.get('owner_ids')
        if owner_ids is None:
            try:
                from flask_login import current_user
                owner_ids = (current_user.id,) if current_user.is_authenticated else ()
            except Exception:
                owner_ids = ()

        externals = {}
        header_imports = []          # modules a dependency needs, declared first
        deps = []                    # Rule objects, in declaration order
        current_rule_text = content
        max_attempts = 10 + 2 * self.MAX_DEPENDENCIES

        for _attempt in range(max_attempts):
            parts = [f'import "{m}"' for m in header_imports] + [d.to_string or '' for d in deps]
            source_text = '\n\n'.join(parts + [current_rule_text])
            try:
                yara.compile(source=source_text, externals=externals)
                risk = detect_global_rule_risk(current_rule_text)
                warnings = list(risk['reasons'])
                if deps:
                    warnings.append("Compiles together with the rule(s) it references: "
                                    + ", ".join(d.title for d in deps) + ".")
                return ValidationResult(ok=True, errors=[], warnings=warnings,
                                        normalized_content=current_rule_text, dependencies=deps)

            except yara.SyntaxError as e:
                error_msg = str(e)
                match_id = re.search(r'undefined identifier "(\w+)"', error_msg)
                if not match_id:
                    return ValidationResult(ok=False, errors=[error_msg], normalized_content=current_rule_text)
                var_name = match_id.group(1)

                if var_name in self.YARA_MODULES:
                    own_uses = not deps or re.search(rf'\b{var_name}\.', current_rule_text)
                    own_imports = re.search(rf'import\s+"{var_name}"', current_rule_text)
                    if own_uses and not own_imports:
                        # the rule's own fix — kept in its saved text, as before
                        current_rule_text = insert_import_module(current_rule_text, var_name)
                    elif var_name not in header_imports:
                        # a rule it depends on needs the module: declared first
                        header_imports.append(var_name)
                    else:
                        return ValidationResult(ok=False, errors=[error_msg], normalized_content=current_rule_text)
                    continue

                if var_name in ALLOWED_EXTERNALS:
                    externals[var_name] = "dummy_value"
                    continue

                if resolve:
                    known = next((d for d in deps if d.title == var_name), None)
                    if known is not None and deps.index(known) != 0:
                        # Declared, but after the rule that uses it: move it first.
                        deps.remove(known)
                        deps.insert(0, known)
                        continue
                    if known is None and len(deps) < self.MAX_DEPENDENCIES:
                        dep = find_trusted_dependency_rule(var_name, rule_id=self_id, source=kwargs.get('source'),
                                                           github_path=kwargs.get('github_path'),
                                                           owner_ids=owner_ids)
                        if dep is not None and dep.id != self_id and dep not in deps:
                            deps.insert(0, dep)
                            continue
                    if known is None and len(deps) >= self.MAX_DEPENDENCIES:
                        error_msg += f" (more than {self.MAX_DEPENDENCIES} referenced rules)"

                return ValidationResult(ok=False, errors=[error_msg], normalized_content=current_rule_text,
                                        dependencies=deps)

            except Exception as e:
                return ValidationResult(ok=False, errors=[str(e)], normalized_content=current_rule_text)

        return ValidationResult(ok=False, errors=["Max validation attempts exceeded"],
                                normalized_content=current_rule_text)

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



  