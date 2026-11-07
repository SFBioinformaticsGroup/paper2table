from typing import Any, Optional

from pydantic import Field
from utils.column_type import (
    ColumnType,
    StrColumnType,
    IntColumnType,
    FloatColumnType,
    BoolColumnType,
)
from utils.enum_type import EnumColumnType
from utils.example_type import ExampleColumnType
from utils.regexp_type import RegexpColumnType
from utils.read_path import read_path
from utils.scientific_name_type import ScientificNameColumnType
from utils.tokenize_schema import tokenize_schema_columns


_types_map: dict[str, type[ColumnType]] = {
    "str": StrColumnType,
    "int": IntColumnType,
    "float": FloatColumnType,
    "bool": BoolColumnType,
    "scientific_name": ScientificNameColumnType,
    "enum": EnumColumnType,
    "example": ExampleColumnType,
    "regexp": RegexpColumnType,
}


class ColumnSchema:
    def __init__(self, columns: dict[str, ColumnType]):
        self._columns = dict(columns)

    def column_names(self) -> list[str]:
        return list(self._columns.keys())

    def column_type(self, name: str) -> ColumnType:
        return self._columns[name]

    def definitions(self) -> list[tuple[str, ColumnType]]:
        return list(self._columns.items())

    def __contains__(self, name: str) -> bool:
        return name in self._columns

    def __bool__(self) -> bool:
        return bool(self._columns)

    def serialize(self) -> dict[str, str]:
        return {col: str(col_type) for col, col_type in self._columns.items()}

    @staticmethod
    def parse(schema_str: str) -> "ColumnSchema":
        columns: dict[str, ColumnType] = {}
        for tokens in tokenize_schema_columns(schema_str):
            if ":" not in tokens:
                raise ValueError(
                    f"Invalid field specifier: {tokens}. Verify your schema"
                )
            [name, type_name, *args] = tokens.split(":", 3)
            columns[name] = ColumnSchema._parse_column_type(
                type_name, args[0].split(",") if args else []
            )
        return ColumnSchema(columns)

    @staticmethod
    def _parse_column_type(type_name: str, args: list[str]) -> ColumnType:
        if type_name in _types_map:
            return _types_map[type_name].build(*args)

        raise ValueError(f"Unsupported type: '{type_name}'. Verify your schema")

    @staticmethod
    def from_settings_dict(schema_dict: dict[str, str]) -> Optional["ColumnSchema"]:
        if not schema_dict:
            return None
        return ColumnSchema.parse(" ".join(f"{k}:{v}" for k, v in schema_dict.items()))

    @staticmethod
    def parse_pydantic(schema_str: str) -> dict[str, tuple[Any, ...]]:
        result = {}
        for name, col_type in ColumnSchema.parse(schema_str).definitions():
            desc = col_type.type_description()
            pydantic_type = col_type.as_type()
            result[name] = (
                pydantic_type,
                Field(..., description=desc) if desc else ...,
            )
        return result


def try_parse_schema(args) -> ColumnSchema | None:
    schema_str = read_path(args.schema_path, inline=args.schema)
    if schema_str:
        return ColumnSchema.parse(schema_str)
