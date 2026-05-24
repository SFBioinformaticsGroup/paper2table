import re


def normalize_str_value(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).lower()


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
