
from utils.normalize_name import normalize_name
from utils.columns_schema import tokenize_schema

def parse_column_names_hints(hints: str) -> list[str]:
    return [normalize_name(hint) for hint in tokenize_schema(hints)]
