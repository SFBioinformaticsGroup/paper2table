import pytest

from utils.column_schema import ColumnSchema, scientific_name


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


def test_parse_pydantic_plain_types_use_ellipsis():
    result = ColumnSchema.parse_pydantic("family:str count:int")
    assert result["family"] == (str, ...)
    assert result["count"] == (int, ...)


def test_parse_pydantic_scientific_name_includes_description():
    result = ColumnSchema.parse_pydantic("species:scientific_name")
    typ, field_info = result["species"]
    assert typ is scientific_name
    assert "binomial nomenclature" in field_info.description


def test_parse_scientific_name_type():
    schema = ColumnSchema.parse("species:scientific_name")
    assert schema.column_type("species") is scientific_name


def test_serialize_scientific_name_type():
    schema = ColumnSchema({"species": scientific_name})
    assert schema.serialize() == {"species": "scientific_name"}


def test_scientific_name_is_str_subclass():
    assert issubclass(scientific_name, str)
