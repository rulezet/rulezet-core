"""
Unit tests for the Sigma driver's condition evaluator
(app/features/rule_tester/drivers/sigma_driver.py).

Internal ref A0: `_eval_condition` used to hand a substituted-but-
unsanitised expression string straight to Python's `eval()`. These
tests prove the replacement AST-based boolean evaluator
(`_safe_bool_eval`) never executes arbitrary code and that ordinary
Sigma conditions still evaluate the same as before.
"""
from __future__ import annotations

import textwrap

import pytest

from app.features.rule_tester.drivers.sigma_driver import SigmaDriver, _safe_bool_eval


def _noop_log(level, message):
    pass


def _run(rule_yaml: str, event: dict):
    driver = SigmaDriver()
    return driver.run_test(rule_yaml, {'type': 'json', 'value': event}, _noop_log)


def test_a0_sigma_eval_condition_blocks_code_execution():
    """A sandbox-escape payload in `condition` must never execute and must not crash the driver."""
    driver = SigmaDriver()

    payload_expressions = [
        "().__class__.__base__.__subclasses__()",
        "__import__('os').system('id')",
        "selection1 or ().__class__.__base__.__subclasses__()",
    ]

    for expr in payload_expressions:
        # _eval_condition() does its own name->True/False substitution before
        # reaching _safe_bool_eval(); calling the private method directly with
        # an empty groups mapping exercises the exact code path that used to
        # reach eval() unchanged when the substitution missed a token.
        result = driver._eval_condition(expr, {'selection1': True})
        assert isinstance(result, bool)

    # Also prove the low-level guard rejects the payload outright rather than
    # silently returning something derived from it.
    with pytest.raises((SyntaxError, ValueError)):
        _safe_bool_eval("().__class__.__base__.__subclasses__()")
    with pytest.raises((SyntaxError, ValueError)):
        _safe_bool_eval("__import__('os').system('id')")


def test_a0_sigma_eval_condition_still_evaluates_valid_conditions():
    """Ordinary Sigma conditions must evaluate the same as with the old eval()-based logic."""
    driver = SigmaDriver()

    groups = {'selection1': True, 'selection2': False}
    assert driver._eval_condition('selection1 and not selection2', groups) is True
    assert driver._eval_condition('selection1 and selection2', groups) is False
    assert driver._eval_condition('selection1 or selection2', groups) is True

    multi_groups = {'selection_a': True, 'selection_b': False, 'selection_c': True}
    assert driver._eval_condition('1 of selection_*', multi_groups) is True
    assert driver._eval_condition('all of selection_*', multi_groups) is False
    assert driver._eval_condition('all of them', multi_groups) is False
    assert driver._eval_condition('any of them', multi_groups) is True


def test_a0_sigma_run_test_end_to_end_with_malicious_condition():
    """Full run_test() path with a hostile condition string must return a safe MatchDetail, not raise."""
    rule_yaml = textwrap.dedent(
        """\
        title: test rule
        logsource:
          category: process_creation
        detection:
          selection1:
            CommandLine: 'evil.exe'
          condition: "selection1 or ().__class__.__base__.__subclasses__()"
        """
    )
    event = {'CommandLine': 'benign.exe'}

    result = _run(rule_yaml, event)

    assert result.error is None
    assert isinstance(result.matched, bool)
