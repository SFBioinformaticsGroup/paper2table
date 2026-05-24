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
        return not value.strip()
    if isinstance(value, list):
        return all(not _str_from_value(v).strip() for v in value)
    return False
