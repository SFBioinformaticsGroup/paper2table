
from utils.column_names import normalize_column_name
from utils.tokenize_schema import tokenize_schema

def parse_column_names_hints(hints: str) -> list[str]:
    return [normalize_column_name(hint) for hint in tokenize_schema(hints)]  # pyright: ignore[reportReturnType]
