_BOOL_TRUE = {"true", "1", "yes", "on"}
_BOOL_FALSE = {"false", "0", "no", "off"}


# TODO we should probably use pandas here
def coerce_str(value: str, target_type: type) -> str:
    """Try to parse value as target_type and return its canonical string form.

    Returns the original value unchanged if conversion fails or if target_type is str.
    bool coercion uses explicit truthy/falsy word sets rather than Python's bool(str),
    which would always return True for non-empty strings.
    """
    if target_type is str:
        return value
    try:
        if target_type is bool:
            lowered = value.lower()
            if lowered in _BOOL_TRUE:
                return "True"
            if lowered in _BOOL_FALSE:
                return "False"
            return value
        if target_type is int:
            return str(int(float(value)))
        return str(target_type(value))
    except (ValueError, TypeError):
        return value
