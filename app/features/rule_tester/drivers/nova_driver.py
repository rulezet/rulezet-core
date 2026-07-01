from .base import BaseTesterDriver, ValidationResult, MatchDetail
from .registry import register_driver


@register_driver('nova')
class NovaDriver(BaseTesterDriver):
    format_name  = 'nova'
    display_name = 'Nova'
    input_types  = ['text']
    can_execute  = False  # pending format spec

    def validate_syntax(self, rule_content: str) -> ValidationResult:
        if not rule_content.strip():
            return ValidationResult(valid=False, errors=['Empty rule content'])
        return ValidationResult(valid=True,
                                warnings=['Nova full validation not yet implemented'])

    def run_test(self, rule_content: str, input_data: dict, log_fn) -> MatchDetail:
        log_fn('warning', 'Nova driver — full execution not yet implemented (pending format spec)')
        return MatchDetail(
            matched=False,
            score=0.0,
            details={'mode': 'not_implemented'},
            quality_hints=['Nova testing engine is under development'],
            error='Nova execution not yet available',
        )
