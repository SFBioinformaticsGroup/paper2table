from typing import Any

from pydantic import Field
from utils.tokenize_schema import tokenize_schema


class scientific_name(str):
    pydantic_field_description = (
        "A taxonomical name in binomial nomenclature (e.g. Homo sapiens)"
    )


def pydantic_field_description(typ: type) -> str | None:
    return getattr(typ, "pydantic_field_description", None)


_types_map: dict[str, type] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "scientific_name": scientific_name,
}
_reverse_types_map: dict[type, str] = {v: k for k, v in _types_map.items()}


class ColumnSchema:
    def __init__(self, columns: dict[str, type]):
        self._columns = dict(columns)

    def column_names(self) -> list[str]:
        return list(self._columns.keys())

    def column_type(self, name: str) -> type:
        return self._columns[name]

    def definitions(self) -> list[tuple[str, type]]:
        return list(self._columns.items())

    def __contains__(self, name: str) -> bool:
        return name in self._columns

    def __bool__(self) -> bool:
        return bool(self._columns)

    def serialize(self) -> dict[str, str]:
        return {col: _reverse_types_map[typ] for col, typ in self._columns.items()}

    @staticmethod
    def parse(schema_str: str) -> "ColumnSchema":
        columns: dict[str, type] = {}
        for part in tokenize_schema(schema_str):
            if ":" not in part:
                raise ValueError(f"Invalid field specifier: {part}. Verify your schema")
            name, type_str = part.split(":", 1)
            if type_str not in _types_map:
                raise ValueError(f"Unsupported type: {type_str}. Verify your schema")
            columns[name] = _types_map[type_str]
        return ColumnSchema(columns)

    def pydantic_field_description(self, name: str) -> str | None:
        return pydantic_field_description(self._columns[name])

    @staticmethod
    def parse_pydantic(schema_str: str) -> dict[str, tuple[Any, ...]]:
        result = {}
        for name, typ in ColumnSchema.parse(schema_str).definitions():
            desc = pydantic_field_description(typ)
            result[name] = (typ, Field(..., description=desc) if desc else ...)
        return result
