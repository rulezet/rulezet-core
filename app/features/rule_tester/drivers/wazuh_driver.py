import re
import time

from .base import BaseTesterDriver, ValidationResult, MatchDetail
from .registry import register_driver

try:
    import xml.etree.ElementTree as ET
    _XML_AVAILABLE = True
except ImportError:
    _XML_AVAILABLE = False


@register_driver('wazuh')
class WazuhDriver(BaseTesterDriver):
    format_name  = 'wazuh'
    display_name = 'Wazuh'
    input_types  = ['syslog_line', 'json_event']
    can_execute  = True

    def validate_syntax(self, rule_content: str) -> ValidationResult:
        if not _XML_AVAILABLE:
            return ValidationResult(valid=False, errors=['xml.etree not available'])
        try:
            root = ET.fromstring(rule_content.strip())
        except ET.ParseError as e:
            return ValidationResult(valid=False, errors=[f'XML parse error: {e}'])

        errors, warnings = [], []
        tag = root.tag.lower()
        if tag not in ('rule', 'group'):
            errors.append(f"Root element must be <rule> or <group>, got <{root.tag}>")

        rules = [root] if tag == 'rule' else root.findall('rule')
        for r in rules:
            if r.get('id') is None:
                warnings.append("Rule missing 'id' attribute")
            if r.find('description') is None:
                warnings.append('Rule missing <description>')

        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def run_test(self, rule_content: str, input_data: dict, log_fn) -> MatchDetail:
        import json as _json

        input_type  = input_data.get('type', 'syslog_line')
        input_value = input_data.get('value', '')

        if input_type == 'json_event':
            try:
                event_obj = _json.loads(input_value) if isinstance(input_value, str) else input_value
                event_str = _json.dumps(event_obj)
            except Exception:
                event_str = str(input_value)
        else:
            event_str = str(input_value)

        log_fn('info', 'Evaluating Wazuh XML rule against event…')
        t0 = time.monotonic()

        try:
            root = ET.fromstring(rule_content.strip())
        except Exception as e:
            return MatchDetail(matched=False, score=0.0, details={},
                               quality_hints=[], error=f'XML parse error: {e}')

        rules = [root] if root.tag.lower() == 'rule' else root.findall('rule')
        conditions_evaluated = []
        overall_matched = False

        for rule_el in rules:
            rule_id = rule_el.get('id', 'unknown')
            rule_matched = True

            for child in rule_el:
                tag_lower = child.tag.lower()
                if tag_lower in ('match', 'regex'):
                    pattern = (child.text or '').strip()
                    if tag_lower == 'match':
                        hit = pattern.lower() in event_str.lower()
                    else:
                        try:
                            hit = bool(re.search(pattern, event_str, re.IGNORECASE))
                        except Exception:
                            hit = False
                    if not hit:
                        rule_matched = False
                    conditions_evaluated.append({
                        'rule_id': rule_id,
                        'type':    tag_lower,
                        'pattern': pattern,
                        'matched': hit,
                    })

            if rule_matched and conditions_evaluated:
                overall_matched = True

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        total = len(conditions_evaluated)
        hits  = sum(1 for c in conditions_evaluated if c['matched'])
        score = (hits / total) if total > 0 else (1.0 if overall_matched else 0.0)

        hints = []
        if not overall_matched and total > 0:
            hints.append(f'Only {hits}/{total} match conditions satisfied')

        log_fn('success' if overall_matched else 'info',
               f'{"MATCHED" if overall_matched else "NO MATCH"} — {hits}/{total} conditions '
               f'in {elapsed_ms}ms')

        return MatchDetail(
            matched=overall_matched,
            score=round(min(score, 1.0), 3),
            details={
                'conditions_evaluated': conditions_evaluated,
                'mode':                 'static_analysis',
            },
            quality_hints=hints,
            execution_time_ms=elapsed_ms,
        )
