import re

from utils.column_type import ColumnType


class RegexpColumnType(ColumnType):
    """Column type that validates values against a regular expression.

    Values that do not match are nullified during coercion.
    Values matching the pattern contribute to value-based column detection.
    """
    @classmethod
    def instantiate(cls, *args):
        if len(args) != 1:
            raise ValueError(f"RegexpColumnType takes exactly one regex")
        return cls(args[0])

    def __init__(self, pattern: str):
        self._pattern = re.compile(pattern)
        self._pattern_str = pattern

    def coerce(self, value: str) -> str | None:
        return value if self._pattern.fullmatch(value) else None

    def matches_value(self, value: str) -> bool:
        return bool(self._pattern.fullmatch(value))

    def type_description(self) -> str:
        return f"Must match pattern: {self._pattern_str}"

    def __repr__(self) -> str:
        return f"regexp:{self._pattern_str}"

    def as_type(self) -> type:
        return str
