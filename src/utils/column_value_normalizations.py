import re
from dataclasses import dataclass

from .tokenize_schema import tokenize_schema


@dataclass
class ColumnValueNormalizationRule:
    column: str
    pattern: re.Pattern
    replacement: str


def parse_column_value_normalizations(
    text: str,
) -> list[ColumnValueNormalizationRule]:
    rules: list[ColumnValueNormalizationRule] = []
    for part in tokenize_schema(text):
        parts = part.split(":", 2)
        if len(parts) != 3:
            raise ValueError(
                f"Invalid rule '{part}': expected 'column:original:new'"
            )
        column, original, replacement = parts
        try:
            pattern = re.compile(original, re.IGNORECASE)
        except re.error as error:
            raise ValueError(
                f"Invalid regex in normalization '{part}': {error}"
            )
        rules.append(
            ColumnValueNormalizationRule(
                column=column, pattern=pattern, replacement=replacement
            )
        )
    return rules
