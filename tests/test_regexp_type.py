from utils.regexp_type import RegexpColumnType


def test_coerce_matching_value_returns_value():
    assert RegexpColumnType(r"\d+").coerce("123") == "123"


def test_coerce_non_matching_value_returns_none():
    assert RegexpColumnType(r"\d+").coerce("abc") is None


def test_coerce_partial_match_returns_none():
    assert RegexpColumnType(r"\d+").coerce("123abc") is None


def test_matches_value_returns_true_for_matching_value():
    assert RegexpColumnType(r"\d+").matches_value("123") is True


def test_matches_value_returns_false_for_non_matching_value():
    assert RegexpColumnType(r"\d+").matches_value("abc") is False


def test_matches_value_requires_full_match():
    assert RegexpColumnType(r"\d+").matches_value("123abc") is False


def test_schema_type_str_preserves_pattern():
    assert str(RegexpColumnType(r"\d+")) == r"regexp:\d+"


def test_type_description_contains_pattern():
    assert r"\d+" in RegexpColumnType(r"\d+").type_description()


def test_as_pydantic_type_returns_str():
    assert RegexpColumnType(r"\d+").as_type() is str


def test_complex_pattern():
    regexp_type = RegexpColumnType(r"\d+(\.\d+)?\s*(cm|mm)")
    assert regexp_type.coerce("10 cm") == "10 cm"
    assert regexp_type.coerce("3.5mm") == "3.5mm"
    assert regexp_type.coerce("blue") is None
