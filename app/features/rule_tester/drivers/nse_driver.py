import re
import time
import json as _json

from .base import BaseTesterDriver, ValidationResult, MatchDetail
from .registry import register_driver


@register_driver('nse')
class NseDriver(BaseTesterDriver):
    format_name  = 'nse'
    display_name = 'NSE (Nmap)'
    input_types  = ['host_json']
    can_execute  = False  # static analysis only — never run live scans

    _DESC_RE     = re.compile(r'\bdescription\s*=\s*\[\[(.*?)\]\]', re.DOTALL)
    _CATS_RE     = re.compile(r'\bcategories\s*=\s*\{([^}]+)\}')
    _PORTRULE_RE = re.compile(r'\bportrule\s*=\s*', re.IGNORECASE)
    _HOSTRULE_RE = re.compile(r'\bhostrule\s*=\s*', re.IGNORECASE)
    _PORT_NUM_RE = re.compile(r'\b(\d{2,5})\b')

    def validate_syntax(self, rule_content: str) -> ValidationResult:
        errors, warnings = [], []
        if not self._PORTRULE_RE.search(rule_content) and not self._HOSTRULE_RE.search(rule_content):
            errors.append('Script defines neither portrule nor hostrule — it will never trigger')
        if not self._DESC_RE.search(rule_content):
            warnings.append('Missing description field')
        if not self._CATS_RE.search(rule_content):
            warnings.append('Missing categories field')
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def run_test(self, rule_content: str, input_data: dict, log_fn) -> MatchDetail:
        input_value = input_data.get('value', '')
        try:
            host = _json.loads(input_value) if isinstance(input_value, str) else input_value
        except Exception:
            host = {}

        log_fn('info', 'Static analysis — checking if script portrule matches simulated host…')
        t0 = time.monotonic()

        open_ports = [int(p) for p in (host.get('ports') or []) if str(p).isdigit()]
        is_hostrule = bool(self._HOSTRULE_RE.search(rule_content))
        is_portrule = bool(self._PORTRULE_RE.search(rule_content))

        # extract ports mentioned in the script
        script_ports = [int(p) for p in self._PORT_NUM_RE.findall(rule_content)
                        if 1 <= int(p) <= 65535]

        cats_m = self._CATS_RE.search(rule_content)
        categories = [c.strip().strip('"\'') for c in cats_m.group(1).split(',') if c.strip()] \
                     if cats_m else []

        matching_ports = [p for p in open_ports if p in script_ports]
        would_trigger  = bool(matching_ports) or is_hostrule or not script_ports

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        score = 1.0 if would_trigger else 0.0

        hints = ['Full execution requires a live nmap instance — static analysis only']
        if not open_ports:
            hints.append('No open ports provided in host_json — add "ports": [...] for better analysis')
        if script_ports and not matching_ports:
            hints.append(f'Script targets ports {script_ports[:5]} — none open on simulated host')

        log_fn('info', f'Static analysis complete in {elapsed_ms}ms')

        return MatchDetail(
            matched=would_trigger,
            score=score,
            details={
                'is_portrule':     is_portrule,
                'is_hostrule':     is_hostrule,
                'categories':      categories,
                'script_ports':    script_ports[:20],
                'open_ports':      open_ports,
                'matching_ports':  matching_ports,
                'would_trigger':   would_trigger,
                'mode':            'static_analysis',
            },
            quality_hints=hints,
            execution_time_ms=elapsed_ms,
        )
