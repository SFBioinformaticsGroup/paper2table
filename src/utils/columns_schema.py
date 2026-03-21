from typing import Any

types_map: dict[str, Any] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
}


def parse_schema(schema_str: str) -> dict[str, tuple[Any, ...]]:
    parts = tokenize_schema(schema_str)

    fields: dict[str, tuple[Any, ...]] = {}
    for part in parts:
        if ":" not in part:
            raise ValueError(f"Invalid field specifier: {part}")
        name, type_str = part.split(":", 1)
        if type_str not in types_map:
            raise ValueError(f"Unsupported type: {type_str}")
        fields[name] = (types_map[type_str], ...)

    return fields


def tokenize_schema(hints: str) -> list[str]:
    return [
        part.strip()
        for part in hints.replace(",", " ").replace("\n", " ").split()
        if part.strip()
    ]
