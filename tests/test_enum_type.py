from utils.enum_type import EnumColumnType


def test_coerce_valid_value_returns_value():
    assert EnumColumnType("red", "blue", "green").coerce("red") == "red"


def test_coerce_another_valid_value_returns_value():
    assert EnumColumnType("red", "blue", "green").coerce("blue") == "blue"


def test_coerce_invalid_value_returns_none():
    assert EnumColumnType("red", "blue", "green").coerce("purple") is None


def test_coerce_empty_string_returns_none():
    assert EnumColumnType("red", "blue", "green").coerce("") is None


def test_matches_value_returns_true_for_known_value():
    assert EnumColumnType("red", "blue", "green").matches_value("red") is True


def test_matches_value_returns_false_for_unknown_value():
    assert EnumColumnType("red", "blue", "green").matches_value("purple") is False


def test_matches_value_returns_false_for_empty_string():
    assert EnumColumnType("red", "blue", "green").matches_value("") is False


def test_schema_type_str_preserves_order():
    assert str(EnumColumnType("red", "blue", "green")) == "enum:red,blue,green"


def test_type_description_lists_values():
    assert (
        EnumColumnType("red", "blue", "green").type_description()
        == "Must be one of: red,blue,green"
    )


def test_as_pydantic_type_returns_str():
    assert EnumColumnType("red", "blue", "green").as_type() is str
