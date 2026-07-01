from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ValidationResult:
    valid: bool
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


@dataclass
class MatchDetail:
    """Serialisable result returned by every driver's run_test()."""
    matched: bool
    score: float                    # 0.0 – 1.0
    details: dict                   # free-form, driver-specific
    quality_hints: list             # human-readable improvement hints
    execution_time_ms: int = 0
    error: str = None

    def to_dict(self) -> dict:
        return {
            'matched':           self.matched,
            'score':             self.score,
            'details':           self.details,
            'quality_hints':     self.quality_hints,
            'execution_time_ms': self.execution_time_ms,
            'error':             self.error,
        }


class BaseTesterDriver(ABC):
    format_name: str = ""
    display_name: str = ""
    input_types: list = []
    can_execute: bool = True

    @abstractmethod
    def validate_syntax(self, rule_content: str) -> ValidationResult: ...

    @abstractmethod
    def run_test(
        self,
        rule_content: str,
        input_data: dict,                    # {"type": "string", "value": "..."}
        log_fn: Callable[[str, str], None],  # log_fn(level, message)
    ) -> MatchDetail: ...

    def get_input_schema(self) -> dict:
        return {'input_types': self.input_types}

    def get_capabilities(self) -> dict:
        return {
            'format':       self.format_name,
            'display_name': self.display_name,
            'can_execute':  self.can_execute,
            'input_types':  self.input_types,
        }
