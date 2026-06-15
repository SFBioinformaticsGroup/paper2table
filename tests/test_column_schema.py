import pytest

from utils.column_schema import ColumnSchema


SCHEMA = ColumnSchema({"family": str, "count": int, "ratio": float, "active": bool})


def test_column_names_returns_ordered_list():
    assert SCHEMA.column_names() == ["family", "count", "ratio", "active"]


def test_column_type_returns_correct_type():
    assert SCHEMA.column_type("family") is str
    assert SCHEMA.column_type("count") is int
    assert SCHEMA.column_type("ratio") is float
    assert SCHEMA.column_type("active") is bool


def test_definitions_returns_name_type_pairs():
    assert SCHEMA.definitions() == [
        ("family", str),
        ("count", int),
        ("ratio", float),
        ("active", bool),
    ]


def test_contains_known_column():
    assert "family" in SCHEMA


def test_does_not_contain_unknown_column():
    assert "genus" not in SCHEMA


def test_non_empty_schema_is_truthy():
    assert bool(SCHEMA)


def test_empty_schema_is_falsy():
    assert not ColumnSchema({})


def test_serialize_returns_string_type_names():
    assert SCHEMA.serialize() == {
        "family": "str",
        "count": "int",
        "ratio": "float",
        "active": "bool",
    }


def test_parse_pydantic_returns_pydantic_field_format():
    result = ColumnSchema.parse_pydantic("family:str count:int")
    assert result == {"family": (str, ...), "count": (int, ...)}


def test_column_type_raises_for_unknown_column():
    with pytest.raises(KeyError):
        SCHEMA.column_type("genus")
