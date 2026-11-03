from utils.column_type import (
    BoolColumnType,
    FloatColumnType,
    IntColumnType,
    StrColumnType,
)


def test_str_column_type_coerce_returns_value_unchanged():
    assert StrColumnType().coerce("hello") == "hello"


def test_str_column_type_repr():
    assert str(StrColumnType()) == "str"


def test_str_column_type_as_pydantic_type():
    assert StrColumnType().as_type() is str


def test_int_column_type_coerce_integer_string():
    assert IntColumnType().coerce("7") == 7


def test_int_column_type_coerce_float_string():
    assert IntColumnType().coerce("42.0") == 42


def test_int_column_type_coerce_invalid_returns_original():
    assert IntColumnType().coerce("N/A") == "N/A"


def test_int_column_type_repr():
    assert str(IntColumnType()) == "int"


def test_int_column_type_as_pydantic_type():
    assert IntColumnType().as_type() is int


def test_float_column_type_coerce_integer_string():
    assert FloatColumnType().coerce("1") == 1.0


def test_float_column_type_coerce_float_string():
    assert FloatColumnType().coerce("3.14") == 3.14


def test_float_column_type_coerce_invalid_returns_none():
    assert FloatColumnType().coerce("abc") is None


def test_float_column_type_repr():
    assert str(FloatColumnType()) == "float"


def test_float_column_type_as_pydantic_type():
    assert FloatColumnType().as_type() is float


def test_bool_column_type_coerce_truthy_words():
    assert BoolColumnType().coerce("true") is True
    assert BoolColumnType().coerce("True") is True
    assert BoolColumnType().coerce("1") is True
    assert BoolColumnType().coerce("yes") is True
    assert BoolColumnType().coerce("on") is True


def test_bool_column_type_coerce_falsy_words():
    assert BoolColumnType().coerce("false") is False
    assert BoolColumnType().coerce("False") is False
    assert BoolColumnType().coerce("FALSE") is False
    assert BoolColumnType().coerce("0") is False
    assert BoolColumnType().coerce("no") is False
    assert BoolColumnType().coerce("off") is False


def test_bool_column_type_coerce_unrecognised_returns_original():
    assert BoolColumnType().coerce("maybe") == "maybe"


def test_bool_column_type_repr():
    assert str(BoolColumnType()) == "bool"


def test_bool_column_type_as_pydantic_type():
    assert BoolColumnType().as_type() is bool
