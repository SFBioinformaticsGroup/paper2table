import pytest
from paper2table.agent import parse_schema


def test_parse_schema_space_separated():
    assert parse_schema("name:str age:int") == {"name": (str, ...), "age": (int, ...)}


def test_parse_schema_comma_separated():
    assert parse_schema("name:str, age:int, active:bool") == {
        "name": (str, ...),
        "age": (int, ...),
        "active": (bool, ...),
    }


def test_parse_schema_newline_separated():
    assert parse_schema("height:float\nweight:float") == {
        "height": (float, ...),
        "weight": (float, ...),
    }


def test_parse_schema_invalid_format():
    with pytest.raises(ValueError):
        parse_schema("name-str")


def test_parse_schema_unsupported_type():
    with pytest.raises(ValueError):
        parse_schema("name:dict")
