from typing import Iterable

from .str import normalize_str
from .tokenize_schema import tokenize_schema

# TODO handle other languages
DEFAULT_NA_VALUES = frozenset(
    {
        "n/a",
        "no data",
        "none",
        "not collected",
        "not identified",
        "undefined",
        "undetermined",
    }
)

NA_VALUES = set(DEFAULT_NA_VALUES)


def configure_na_values(values: Iterable[str]) -> None:
    """Replace the module-level NA_VALUES set."""
    NA_VALUES.clear()
    NA_VALUES.update(normalize_str(expression).lower() for expression in values)


def parse_na_values(text: str) -> list[str]:
    """Parse a newline-separated list of na values.

    Blank lines and '#' comments (full-line or inline) are ignored.
    """
    return tokenize_schema(text)


def normalize_column_value(value: str) -> str:
    normalized = normalize_str(value).lower()
    if normalized in NA_VALUES:
        return ""
    return normalized
