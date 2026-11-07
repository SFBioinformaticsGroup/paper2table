import pytest

from utils.column_schema import ColumnSchema
from utils.column_type import (
    StrColumnType,
    IntColumnType,
    FloatColumnType,
    BoolColumnType,
)
from utils.enum_type import EnumColumnType
from utils.example_type import ExampleColumnType
from utils.regexp_type import RegexpColumnType
from utils.scientific_name_type import ScientificNameColumnType


SCHEMA = ColumnSchema(
    {
        "family": StrColumnType(),
        "count": IntColumnType(),
        "ratio": FloatColumnType(),
        "active": BoolColumnType(),
    }
)


def test_column_names_returns_ordered_list():
    assert SCHEMA.column_names() == ["family", "count", "ratio", "active"]


def test_column_type_returns_correct_type_descriptor():
    assert isinstance(SCHEMA.column_type("family"), StrColumnType)
    assert isinstance(SCHEMA.column_type("count"), IntColumnType)
    assert isinstance(SCHEMA.column_type("ratio"), FloatColumnType)
    assert isinstance(SCHEMA.column_type("active"), BoolColumnType)


def test_contains_known_column():
    assert "family" in SCHEMA
    assert "genus" not in SCHEMA


def test_schema_handles_truthyness():
    assert bool(SCHEMA)
    assert not ColumnSchema({})


def test_serialize_returns_string_type_names():
    assert SCHEMA.serialize() == {
        "family": "str",
        "count": "int",
        "ratio": "float",
        "active": "bool",
    }


def test_parse_pydantic_plain_types_use_ellipsis():
    result = ColumnSchema.parse_pydantic("family:str count:int")
    assert result["family"] == (str, ...)
    assert result["count"] == (int, ...)

def test_parse_pydantic_scientific_name_includes_description():
    result = ColumnSchema.parse_pydantic("species:scientific_name")
    pydantic_type, field_info = result["species"]
    assert pydantic_type is str
    assert "binomial nomenclature" in field_info.description


def test_column_type_raises_for_unknown_column():
    with pytest.raises(KeyError):
        SCHEMA.column_type("genus")


def test_serialize_scientific_name_type():
    schema = ColumnSchema({"species": ScientificNameColumnType()})
    assert schema.serialize() == {"species": "scientific_name"}

def test_parse_scientific_name_type():
    schema = ColumnSchema.parse("species:scientific_name")
    assert isinstance(schema.column_type("species"), ScientificNameColumnType)

def test_parse_enum_type():
    schema = ColumnSchema.parse("color:enum:red,blue,green")
    color_type = schema.column_type("color")
    assert isinstance(color_type, EnumColumnType)
    assert color_type.matches_value("red") is True
    assert color_type.matches_value("purple") is False


def test_parse_example_type():
    schema = ColumnSchema.parse("color:example:red,blue,green")
    color_type = schema.column_type("color")
    assert isinstance(color_type, ExampleColumnType)
    assert color_type.matches_value("red") is True
    assert color_type.coerce("purple") == "purple"


def test_parse_regexp_type():
    schema = ColumnSchema.parse(r"size:regexp:\d+")
    size_type = schema.column_type("size")
    assert isinstance(size_type, RegexpColumnType)
    assert size_type.matches_value("123") is True
    assert size_type.coerce("abc") is None


def test_parse_enum_preserves_values_in_order():
    schema = ColumnSchema.parse("color:enum:red,blue,green")
    assert schema.serialize() == {"color": "enum:red,blue,green"}


def test_parse_regexp_round_trips():
    schema = ColumnSchema.parse(r"size:regexp:\d+")
    assert schema.serialize() == {r"size": r"regexp:\d+"}


def test_parse_enum_missing_params_raises_value_error():
    with pytest.raises(ValueError, match="takes one or more values"):
        ColumnSchema.parse("color:enum")


def test_parse_example_missing_params_raises_value_error():
    with pytest.raises(ValueError, match="takes one or more examples"):
        ColumnSchema.parse("color:example")


def test_parse_regexp_missing_params_raises_value_error():
    with pytest.raises(ValueError, match="takes exactly one regex"):
        ColumnSchema.parse(r"size:regexp")


def test_parse_multiple_columns_with_enum():
    schema = ColumnSchema.parse("color:enum:red,blue family:str")
    assert isinstance(schema.column_type("color"), EnumColumnType)
    assert isinstance(schema.column_type("family"), StrColumnType)
    assert schema.column_type("color").matches_value("red") is True
    assert schema.column_type("color").matches_value("purple") is False


def test_parse_enum_and_str_comma_separated():
    schema = ColumnSchema.parse("color:enum:red,blue,family:str")
    assert isinstance(schema.column_type("color"), EnumColumnType)
    assert isinstance(schema.column_type("family"), StrColumnType)


def test_unsupported_type_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported type"):
        ColumnSchema.parse("species:unknown_type")


def test_from_settings_dict_with_enum():
    schema = ColumnSchema.from_settings_dict(
        {"color": "enum:red,blue,green", "family": "str"}
    )
    assert schema is not None
    assert isinstance(schema.column_type("color"), EnumColumnType)
    assert isinstance(schema.column_type("family"), StrColumnType)


def test_column_schema_from_settings_dict_empty():
    result = ColumnSchema.from_settings_dict({})
    assert result is None


def test_column_schema_from_settings_dict_round_trip():
    original_schema = ColumnSchema.parse("family:str,count:int,name:scientific_name")
    serialized = original_schema.serialize()
    reconstructed = ColumnSchema.from_settings_dict(serialized)
    assert reconstructed is not None
    assert reconstructed.serialize() == serialized


def test_column_schema_from_settings_dict_single_field():
    schema = ColumnSchema.from_settings_dict({"family": "str"})
    assert schema is not None
    assert schema.serialize() == {"family": "str"}


def test_parse_schema_space_separated():
    schema = ColumnSchema.parse("name:str age:int")
    assert schema.column_names() == ["name", "age"]
    assert isinstance(schema.column_type("name"), StrColumnType)
    assert isinstance(schema.column_type("age"), IntColumnType)


def test_parse_schema_comma_separated():
    schema = ColumnSchema.parse("name:str, age:int, active:bool")
    assert schema.column_names() == ["name", "age", "active"]
    assert isinstance(schema.column_type("active"), BoolColumnType)


def test_parse_schema_newline_separated():
    schema = ColumnSchema.parse("height:float\nweight:float")
    assert schema.column_names() == ["height", "weight"]
    assert isinstance(schema.column_type("height"), FloatColumnType)
    assert isinstance(schema.column_type("weight"), FloatColumnType)


def test_parse_schema_invalid_format():
    with pytest.raises(ValueError):
        ColumnSchema.parse("name-str")


def test_parse_schema_unsupported_type():
    with pytest.raises(ValueError):
        ColumnSchema.parse("name:dict")


def test_parse_schema_ignores_comments():
    schema = ColumnSchema.parse("family:str # ignored\nspecies:int")
    assert schema.column_names() == ["family", "species"]
    assert isinstance(schema.column_type("family"), StrColumnType)
    assert isinstance(schema.column_type("species"), IntColumnType)
