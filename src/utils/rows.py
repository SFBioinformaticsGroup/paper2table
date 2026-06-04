import re

# TODO handle other languages
NO_DATA_EXPRESSIONS = {"no data", "none"}

NONPRINTABLE_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f�]")


def normalize_str(value: str) -> str:
    value = NONPRINTABLE_RE.sub("", value)
    normalized = re.sub(r"[‐‑‒–—―−]", "-", value)
    return re.sub(r"\s+", " ", normalized.strip())


def normalize_str_value(value: str) -> str:
    normalized = normalize_str(value).lower()
    if normalized in NO_DATA_EXPRESSIONS:
        return ""
    return normalized


def _str_from_value(v) -> str:
    if hasattr(v, "value"):
        return v.value
    if isinstance(v, dict):
        return v.get("value", "")
    return str(v)


def is_empty_value(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not normalize_str_value(value)
    if isinstance(value, list):
        return all(not normalize_str_value(_str_from_value(v)) for v in value)
    return False
