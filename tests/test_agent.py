import pytest

from utils.column_schema import ColumnSchema


def test_parse_schema_space_separated():
    schema = ColumnSchema.parse("name:str age:int")
    assert schema.column_names() == ["name", "age"]
    assert schema.column_type("name") is str
    assert schema.column_type("age") is int


def test_parse_schema_comma_separated():
    schema = ColumnSchema.parse("name:str, age:int, active:bool")
    assert schema.column_names() == ["name", "age", "active"]
    assert schema.column_type("active") is bool


def test_parse_schema_newline_separated():
    schema = ColumnSchema.parse("height:float\nweight:float")
    assert schema.column_names() == ["height", "weight"]
    assert schema.column_type("height") is float
    assert schema.column_type("weight") is float


def test_parse_schema_invalid_format():
    with pytest.raises(ValueError):
        ColumnSchema.parse("name-str")


def test_parse_schema_unsupported_type():
    with pytest.raises(ValueError):
        ColumnSchema.parse("name:dict")
