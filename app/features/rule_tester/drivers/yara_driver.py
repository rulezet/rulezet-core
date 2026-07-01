import binascii
import base64
import time

from .base import BaseTesterDriver, ValidationResult, MatchDetail
from .registry import register_driver


@register_driver('yara')
class YaraDriver(BaseTesterDriver):
    format_name  = 'yara'
    display_name = 'YARA'
    input_types  = ['string', 'hex', 'file_b64']
    can_execute  = True

    def validate_syntax(self, rule_content: str) -> ValidationResult:
        try:
            import yara
            yara.compile(source=rule_content)
            return ValidationResult(valid=True)
        except ImportError:
            return ValidationResult(valid=False, errors=['yara-python not installed'])
        except Exception as e:
            return ValidationResult(valid=False, errors=[str(e)])

    def run_test(self, rule_content: str, input_data: dict, log_fn) -> MatchDetail:
        try:
            import yara
        except ImportError:
            return MatchDetail(matched=False, score=0.0, details={},
                               quality_hints=[], error='yara-python not installed')

        input_type  = input_data.get('type', 'string')
        input_value = input_data.get('value', '')

        log_fn('info', f'Compiling YARA rule ({input_type} input)…')
        t0 = time.monotonic()

        try:
            rules = yara.compile(source=rule_content)
        except yara.SyntaxError as e:
            return MatchDetail(matched=False, score=0.0, details={},
                               quality_hints=[], error=f'Syntax error: {e}')

        compile_ms = int((time.monotonic() - t0) * 1000)

        # convert input to bytes
        try:
            if input_type == 'hex':
                data = bytes.fromhex(input_value.replace(' ', '').replace('\n', ''))
            elif input_type == 'file_b64':
                data = base64.b64decode(input_value)
            else:
                data = input_value.encode('utf-8', errors='replace')
        except Exception as e:
            return MatchDetail(matched=False, score=0.0, details={},
                               quality_hints=[], error=f'Input conversion error: {e}')

        log_fn('info', f'Rule compiled in {compile_ms}ms — scanning {len(data)} bytes…')
        t1 = time.monotonic()

        try:
            matches = rules.match(data=data)
        except Exception as e:
            return MatchDetail(matched=False, score=0.0, details={},
                               quality_hints=[], error=f'Scan error: {e}')

        scan_ms = int((time.monotonic() - t1) * 1000)
        total_ms = compile_ms + scan_ms

        if not matches:
            log_fn('info', f'No match — scan took {scan_ms}ms')
            return MatchDetail(matched=False, score=0.0,
                               details={'mode': 'full_execution'},
                               quality_hints=['Rule did not match the provided input'],
                               execution_time_ms=total_ms)

        # build detail from first match (YARA rules are usually single-rule files)
        m = matches[0]
        strings_matched = []
        total_strings   = 0

        try:
            # yara-python >= 4.x
            for s in m.strings:
                total_strings += 1
                for instance in s.instances:
                    strings_matched.append({
                        'identifier': s.identifier,
                        'offset':     instance.offset,
                        'value_hex':  instance.matched_data.hex(),
                        'length':     instance.matched_length,
                    })
        except AttributeError:
            # fallback for older yara-python
            for offset, identifier, value in getattr(m, 'strings', []):
                total_strings += 1
                strings_matched.append({
                    'identifier': identifier,
                    'offset':     offset,
                    'value_hex':  value.hex() if isinstance(value, bytes) else '',
                })

        string_coverage = (len(strings_matched) / total_strings) if total_strings > 0 else 1.0
        score = min(string_coverage, 1.0)

        hints = []
        if total_strings > 0 and len(strings_matched) < total_strings:
            hints.append(
                f'Only {len(strings_matched)} of {total_strings} strings matched — '
                'consider loosening conditions for broader detection'
            )
        if total_strings == 0:
            hints.append('Rule matched but defines no strings — add strings for higher specificity')
        if compile_ms > 500:
            hints.append(f'Rule compiled in {compile_ms}ms — complex regex may impact performance')

        log_fn('success', f'MATCHED — {len(strings_matched)} string(s) hit in {scan_ms}ms')

        details = {
            'rule_name':       m.rule,
            'tags':            list(m.tags),
            'meta':            dict(m.meta),
            'strings_matched': strings_matched,
            'string_coverage': round(string_coverage, 3),
            'mode':            'full_execution',
        }

        return MatchDetail(matched=True, score=round(score, 3), details=details,
                           quality_hints=hints, execution_time_ms=total_ms)

    @classmethod
    def run_batch(cls, rule_sources: dict, input_data: dict) -> dict:
        """
        Compile many YARA rules at once and scan a single input.
        rule_sources: {str_rule_id: yara_source_code}
        Returns:      {str_rule_id: MatchDetail}
        """
        import yara

        input_type  = input_data.get('type', 'string')
        input_value = input_data.get('value', '')

        # convert input bytes once
        try:
            if input_type == 'hex':
                data = bytes.fromhex(input_value.replace(' ', '').replace('\n', ''))
            elif input_type == 'file_b64':
                data = base64.b64decode(input_value)
            else:
                data = input_value.encode('utf-8', errors='replace')
        except Exception as e:
            err = MatchDetail(matched=False, score=0.0, details={}, quality_hints=[], error=str(e))
            return {rid: err for rid in rule_sources}

        # filter out empty sources
        sources = {rid: src for rid, src in rule_sources.items() if src and src.strip()}
        if not sources:
            empty = MatchDetail(matched=False, score=0.0, details={}, quality_hints=[], error='Empty rule content')
            return {rid: empty for rid in rule_sources}

        t0 = time.monotonic()
        try:
            compiled = yara.compile(sources=sources)
        except Exception as e:
            err = MatchDetail(matched=False, score=0.0, details={}, quality_hints=[], error=str(e))
            return {rid: err for rid in rule_sources}

        compile_ms = int((time.monotonic() - t0) * 1000)

        try:
            matches = compiled.match(data=data, timeout=30)
        except Exception as e:
            err = MatchDetail(matched=False, score=0.0, details={}, quality_hints=[], error=str(e))
            return {rid: err for rid in rule_sources}

        scan_ms = int((time.monotonic() - t0) * 1000)

        matched_ns = {m.namespace: m for m in matches}

        results = {}
        for rid in rule_sources:
            m = matched_ns.get(rid)
            if m is None:
                results[rid] = MatchDetail(matched=False, score=0.0,
                                           details={'mode': 'batch_execution'},
                                           quality_hints=[],
                                           execution_time_ms=scan_ms)
            else:
                strings_matched = []
                try:
                    for s in m.strings:
                        for inst in s.instances:
                            strings_matched.append({'identifier': s.identifier,
                                                    'offset': inst.offset})
                except AttributeError:
                    pass
                results[rid] = MatchDetail(matched=True, score=1.0,
                                           details={'mode': 'batch_execution',
                                                    'rule_name': m.rule,
                                                    'strings_matched': len(strings_matched)},
                                           quality_hints=[],
                                           execution_time_ms=scan_ms)
        return results
