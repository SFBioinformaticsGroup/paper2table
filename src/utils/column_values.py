from .str import normalize_str

# TODO handle other languages
NO_DATA_EXPRESSIONS = {"no data", "none", "not identified"}


def normalize_column_value(value: str) -> str:
    normalized = normalize_str(value).lower()
    if normalized in NO_DATA_EXPRESSIONS:
        return ""
    return normalized