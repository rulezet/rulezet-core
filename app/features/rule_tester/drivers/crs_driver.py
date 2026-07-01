import re
import time

from .base import BaseTesterDriver, ValidationResult, MatchDetail
from .registry import register_driver


@register_driver('crs')
class CrsDriver(BaseTesterDriver):
    format_name  = 'crs'
    display_name = 'CRS (ModSecurity)'
    input_types  = ['http_request']
    can_execute  = True

    _SECRULE_RE = re.compile(
        r'^SecRule\s+(\S+)\s+"([^"]+)"\s+"([^"]+)"',
        re.IGNORECASE | re.MULTILINE,
    )
    _ID_RE    = re.compile(r'\bid:(\d+)',   re.IGNORECASE)
    _MSG_RE   = re.compile(r'\bmsg:\'([^\']+)\'', re.IGNORECASE)
    _SCORE_RE = re.compile(r'setvar[^,]+anomaly_score[^,]*\+(\d+)', re.IGNORECASE)

    def validate_syntax(self, rule_content: str) -> ValidationResult:
        errors, warnings = [], []
        if not re.search(r'\bSecRule\b', rule_content, re.IGNORECASE):
            errors.append('No SecRule directive found')
        if not re.search(r'\bid:\d+', rule_content, re.IGNORECASE):
            warnings.append('Rule has no id action — recommended for all production rules')
        return ValidationResult(valid=len(errors) == 0, errors=errors, warnings=warnings)

    def run_test(self, rule_content: str, input_data: dict, log_fn) -> MatchDetail:
        import json as _json

        input_type  = input_data.get('type', 'http_request')
        input_value = input_data.get('value', '')

        try:
            req = _json.loads(input_value) if isinstance(input_value, str) else input_value
        except Exception as e:
            return MatchDetail(matched=False, score=0.0, details={},
                               quality_hints=[], error=f'Invalid JSON request: {e}')

        method  = req.get('method', 'GET').upper()
        url     = req.get('url', '/')
        headers = req.get('headers') or {}
        body    = req.get('body', '')

        # build variable map
        variables = {
            'REQUEST_METHOD':  method,
            'REQUEST_URI':     url,
            'REQUEST_LINE':    f'{method} {url} HTTP/1.1',
            'REQUEST_BODY':    body,
            'ARGS':            url.split('?', 1)[-1] if '?' in url else '',
            'ARGS_COMBINED_SIZE': str(len(url) + len(body)),
        }
        for hk, hv in headers.items():
            variables[f'REQUEST_HEADERS:{hk}'] = hv
            variables['REQUEST_HEADERS'] = variables.get('REQUEST_HEADERS', '') + f' {hv}'

        log_fn('info', f'Evaluating CRS SecRule against {method} {url[:60]}…')
        t0 = time.monotonic()

        triggered, total_anomaly_score = [], 0
        for m in self._SECRULE_RE.finditer(rule_content):
            var_name, operator, actions = m.group(1), m.group(2), m.group(3)

            # resolve variable value
            target = ''
            for part in re.split(r'[|,]', var_name):
                part = part.strip().upper()
                target += ' ' + variables.get(part, '')

            hit = self._apply_operator(operator, target.strip())

            if hit:
                rule_id = self._ID_RE.search(actions)
                msg     = self._MSG_RE.search(actions)
                score_m = self._SCORE_RE.search(actions)
                score_n = int(score_m.group(1)) if score_m else 0
                total_anomaly_score += score_n
                triggered.append({
                    'rule_id':      rule_id.group(1) if rule_id else '?',
                    'msg':          msg.group(1) if msg else '?',
                    'variable':     var_name,
                    'operator':     operator[:60],
                    'anomaly_score': score_n,
                })

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        matched = len(triggered) > 0
        score   = min(total_anomaly_score / 25.0, 1.0)

        hints = []
        if not matched:
            hints.append('No SecRule triggered — request appears clean for this rule set')
        elif total_anomaly_score >= 25:
            hints.append(f'High anomaly score ({total_anomaly_score}) — request would be blocked at default threshold')
        else:
            hints.append(f'Anomaly score {total_anomaly_score} — below default blocking threshold (25)')

        log_fn('success' if matched else 'info',
               f'{"MATCHED" if matched else "NO MATCH"} — anomaly score {total_anomaly_score} '
               f'in {elapsed_ms}ms')

        return MatchDetail(
            matched=matched,
            score=round(score, 3),
            details={
                'triggered_rules':    triggered,
                'total_anomaly_score': total_anomaly_score,
                'mode':               'static_analysis',
            },
            quality_hints=hints,
            execution_time_ms=elapsed_ms,
        )

    def _apply_operator(self, operator: str, target: str) -> bool:
        op = operator.lower()
        if op.startswith('@rx ') or op.startswith('@regex '):
            pattern = operator.split(' ', 1)[1]
            try:
                return bool(re.search(pattern, target, re.IGNORECASE))
            except Exception:
                return False
        if op.startswith('@contains '):
            needle = operator.split(' ', 1)[1]
            return needle.lower() in target.lower()
        if op.startswith('@streq '):
            return operator.split(' ', 1)[1].lower() == target.lower()
        if op.startswith('@beginswith '):
            return target.lower().startswith(operator.split(' ', 1)[1].lower())
        if op.startswith('@endswith '):
            return target.lower().endswith(operator.split(' ', 1)[1].lower())
        if op.startswith('@detectsqli'):
            sqli_patterns = ["'", '"', '--', ';--', 'select ', 'union ', 'drop ', 'insert ']
            return any(p in target.lower() for p in sqli_patterns)
        if op.startswith('@detectxss'):
            xss_patterns = ['<script', 'javascript:', 'onerror=', 'onload=']
            return any(p in target.lower() for p in xss_patterns)
        # default: simple contains
        return operator.lower() in target.lower()
