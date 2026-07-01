import re
import time
import json as _json

from .base import BaseTesterDriver, ValidationResult, MatchDetail
from .registry import register_driver


@register_driver('zeek')
class ZeekDriver(BaseTesterDriver):
    format_name  = 'zeek'
    display_name = 'Zeek'
    input_types  = ['zeek_log_json']
    can_execute  = False  # static analysis only

    _EVENT_RE  = re.compile(r'\bevent\s+(\w+)\s*\(', re.MULTILINE)
    _MODULE_RE = re.compile(r'\bmodule\s+(\w+)\s*;', re.MULTILINE)

    def validate_syntax(self, rule_content: str) -> ValidationResult:
        errors, warnings = [], []
        if not self._EVENT_RE.search(rule_content):
            warnings.append('No event hook found — script may not trigger on any log source')
        if 'redef' not in rule_content and 'export' not in rule_content:
            pass
        return ValidationResult(valid=True, errors=errors, warnings=warnings)

    def run_test(self, rule_content: str, input_data: dict, log_fn) -> MatchDetail:
        input_value = input_data.get('value', '')
        try:
            event_obj = _json.loads(input_value) if isinstance(input_value, str) else input_value
        except Exception:
            event_obj = {}

        log_fn('info', 'Static analysis — matching Zeek event hooks against log type…')
        t0 = time.monotonic()

        events_defined = self._EVENT_RE.findall(rule_content)
        log_type = (event_obj.get('_path') or event_obj.get('log_type') or '').lower()

        # map common event names to log types
        event_log_map = {
            'connection_established': 'conn',
            'http_request': 'http',
            'http_reply': 'http',
            'dns_request': 'dns',
            'dns_message': 'dns',
            'ssl_client_hello': 'ssl',
            'ssl_established': 'ssl',
            'new_connection': 'conn',
            'log_write': '*',
        }

        matched_events = []
        for ev in events_defined:
            expected_log = event_log_map.get(ev, '')
            if expected_log in ('*', log_type) or (log_type and log_type in ev.lower()):
                matched_events.append(ev)

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        matched = bool(matched_events) or (not log_type and bool(events_defined))
        score   = 1.0 if matched else 0.0

        hints = []
        if not events_defined:
            hints.append('No event hooks found — verify script structure')
        if log_type and not matched_events:
            hints.append(f'Log type "{log_type}" does not match any event hooks in this script')
        hints.append('Full execution requires a live Zeek instance — static analysis only')

        log_fn('info', f'Static analysis complete in {elapsed_ms}ms — '
               f'{len(events_defined)} event hook(s) found')

        return MatchDetail(
            matched=matched,
            score=score,
            details={
                'events_defined':  events_defined,
                'log_type_tested': log_type or 'unknown',
                'matched_events':  matched_events,
                'mode':            'static_analysis',
            },
            quality_hints=hints,
            execution_time_ms=elapsed_ms,
        )
