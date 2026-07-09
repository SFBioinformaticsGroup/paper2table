from utils.coerce import coerce_str
from utils.column_schema import scientific_name


def test_str_is_noop():
    assert coerce_str("hello", str) == "hello"


def test_int_normalizes_float_string():
    assert coerce_str("42.0", int) == "42"


def test_int_plain():
    assert coerce_str("7", int) == "7"


def test_int_invalid_leaves_unchanged():
    assert coerce_str("N/A", int) == "N/A"


def test_float_from_int_string():
    assert coerce_str("1", float) == "1.0"


def test_float_plain():
    assert coerce_str("3.14", float) == "3.14"


def test_float_invalid_leaves_unchanged():
    assert coerce_str("abc", float) == "abc"


def test_bool_truthy_words():
    for word in ("true", "True", "TRUE", "1", "yes", "YES", "on", "ON"):
        assert coerce_str(word, bool) == "True", word


def test_bool_falsy_words():
    for word in ("false", "False", "FALSE", "0", "no", "NO", "off", "OFF"):
        assert coerce_str(word, bool) == "False", word


def test_bool_unrecognised_leaves_unchanged():
    assert coerce_str("maybe", bool) == "maybe"


def test_scientific_name_is_noop():
    assert coerce_str("Homo sapiens", scientific_name) == "Homo sapiens"
