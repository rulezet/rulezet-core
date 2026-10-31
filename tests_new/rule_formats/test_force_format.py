"""Issue #9 — a rule format forced at import for files whose extension no format recognises."""
import asyncio

from app.core.db_class.rule import Rule
from app.features.rule.rule_format import main_format as M
from app.features.rule.rule_format.abstract_rule_type.rule_type_abstract import RuleType

YARA = 'rule forced_format_test {\n    strings:\n        $a = "forced"\n    condition:\n        $a\n}'


def _instances():
    M.load_all_rule_formats()
    return [cls() for cls in RuleType.__subclasses__()]


def test_only_a_known_format_and_never_docs_or_code(app):
    with app.app_context():
        from app.features.rule.rule import _import_force_format
        assert _import_force_format("YARA") == "yara" and _import_force_format("nope") is None
        assert _import_force_format(None) is None and _import_force_format("") is None
        assert M.forced_format_instance("yara", _instances()).format.lower() == "yara"
    assert M.forced_format_claims("rules") and M.forced_format_claims("et.conf") and M.forced_format_claims("x.sig")
    assert not any(M.forced_format_claims(f) for f in ("README.md", "logo.png", "tool.py", "dump.pcap", "a.zip"))


def test_file_without_extension_imported_in_the_forced_format(app, users, tmp_path):
    (tmp_path / "my_rules").write_text(YARA)                 # no extension: no format claims it
    (tmp_path / "README.md").write_text(YARA)                # a doc file: never read, even forced
    with app.app_context():
        info = {"origin": "zip_upload", "url": "zip_upload", "repo_url": "forced format test", "license": "MIT"}
        _, imported, _ = asyncio.run(M.extract_rule_from_repo(str(tmp_path), info, users.owner))
        assert imported == 0                                  # without the option: skipped as before
        _, imported, _ = asyncio.run(M.extract_rule_from_repo(str(tmp_path), {**info, "force_format": "yara"}, users.owner))
        assert imported == 1
        assert Rule.query.filter(Rule.to_string.contains("forced_format_test")).count() == 1
