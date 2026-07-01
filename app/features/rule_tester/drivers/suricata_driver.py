import re
import time

from .base import BaseTesterDriver, ValidationResult, MatchDetail
from .registry import register_driver


@register_driver('suricata')
class SuricataDriver(BaseTesterDriver):
    format_name  = 'suricata'
    display_name = 'Suricata'
    input_types  = ['http_request', 'hex_payload', 'text_payload']
    can_execute  = True   # static analysis always available

    # Suricata option regex
    _SID_RE  = re.compile(r'\bsid\s*:\s*(\d+)', re.IGNORECASE)
    _MSG_RE  = re.compile(r'\bmsg\s*:\s*"([^"]*)"', re.IGNORECASE)
    _PROTO_RE = re.compile(r'^(alert|drop|pass|reject)\s+(\w+)', re.IGNORECASE)
    _CONTENT_RE = re.compile(r'\bcontent\s*:\s*"([^"]*)"', re.IGNORECASE)
    _PCRE_RE    = re.compile(r'\bpcre\s*:\s*"([^"]*)"', re.IGNORECASE)

    def validate_syntax(self, rule_content: str) -> ValidationResult:
        errors, warnings = [], []
        lines = [l.strip() for l in rule_content.splitlines() if l.strip() and not l.startswith('#')]
        if not lines:
            return ValidationResult(valid=False, errors=['Empty rule'])
        for line in lines:
            if not self._PROTO_RE.match(line):
                errors.append(f'Line does not start with action+protocol: {line[:60]}')
            if 'sid:' not in line.lower():
                warnings.append('Rule is missing sid option')
            if 'msg:' not in line.lower():
                warnings.append('Rule is missing msg option')
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def run_test(self, rule_content: str, input_data: dict, log_fn) -> MatchDetail:
        input_type  = input_data.get('type', 'text_payload')
        input_value = input_data.get('value', '')

        log_fn('info', 'Static analysis mode — scanning content keywords against payload…')
        t0 = time.monotonic()

        # extract rule fields
        sid_m   = self._SID_RE.search(rule_content)
        msg_m   = self._MSG_RE.search(rule_content)
        proto_m = self._PROTO_RE.search(rule_content)
        keywords = self._CONTENT_RE.findall(rule_content)
        pcres    = self._PCRE_RE.findall(rule_content)

        # build payload string
        if input_type == 'hex_payload':
            try:
                payload = bytes.fromhex(input_value.replace(' ', '')).decode('latin-1')
            except Exception:
                payload = input_value
        elif input_type == 'http_request':
            import json as _json
            try:
                req = _json.loads(input_value) if isinstance(input_value, str) else input_value
                parts = [f"{req.get('method','GET')} {req.get('url','/')} HTTP/1.1"]
                for h, v in (req.get('headers') or {}).items():
                    parts.append(f'{h}: {v}')
                parts.append('')
                parts.append(req.get('body', ''))
                payload = '\r\n'.join(parts)
            except Exception:
                payload = str(input_value)
        else:
            payload = str(input_value)

        keywords_found = [k for k in keywords if k.lower() in payload.lower()]
        pcre_matches = []
        for pattern in pcres:
            stripped = re.sub(r'/[gimsuy]*$', '', pattern.lstrip('/'))
            try:
                if re.search(stripped, payload, re.IGNORECASE):
                    pcre_matches.append(pattern)
            except Exception:
                pass

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        total = len(keywords) + len(pcres)
        hits  = len(keywords_found) + len(pcre_matches)

        matched = hits > 0 or (total == 0 and bool(payload))
        score   = min(hits / total, 1.0) if total > 0 else (0.5 if matched else 0.0)

        hints = []
        if pcres:
            hints.append('Rule uses PCRE — may impact performance at high traffic volumes')
        if keywords and not any('fast_pattern' in rule_content.lower() for _ in [1]):
            hints.append('No fast_pattern keyword — consider adding for performance')
        if total > 0 and hits < total:
            hints.append(f'Only {hits}/{total} content keywords matched the payload')

        log_fn('success' if matched else 'info',
               f'{"MATCHED" if matched else "NO MATCH"} — {hits}/{total} keywords hit '
               f'(static mode, {elapsed_ms}ms)')

        return MatchDetail(
            matched=matched,
            score=round(score, 3),
            details={
                'sid':                  sid_m.group(1) if sid_m else None,
                'msg':                  msg_m.group(1) if msg_m else None,
                'proto':                proto_m.group(2) if proto_m else None,
                'content_keywords':     keywords,
                'keywords_found':       keywords_found,
                'pcre_patterns':        pcres,
                'pcre_matches':         pcre_matches,
                'estimated_performance': 'high' if pcres else ('medium' if keywords else 'low'),
                'mode':                 'static_analysis',
            },
            quality_hints=hints,
            execution_time_ms=elapsed_ms,
        )
