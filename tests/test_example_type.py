from utils.example_type import ExampleColumnType


def test_coerce_known_example_returns_value():
    assert ExampleColumnType("red", "blue").coerce("red") == "red"


def test_coerce_unknown_value_also_returns_value():
    assert ExampleColumnType("red", "blue").coerce("purple") == "purple"


def test_coerce_empty_string_returns_empty_string():
    assert ExampleColumnType("red", "blue").coerce("") == ""


def test_matches_value_returns_true_for_known_example():
    assert ExampleColumnType("red", "blue").matches_value("red") is True


def test_matches_value_returns_false_for_unknown_value():
    assert ExampleColumnType("red", "blue").matches_value("purple") is False


def test_schema_type_str_preserves_order():
    assert str(ExampleColumnType("red", "blue")) == "example:red,blue"


def test_type_description_lists_examples():
    description = ExampleColumnType("red", "blue").type_description()
    assert "red" in description
    assert "blue" in description
    assert "other" in description.lower() or "also valid" in description.lower()


def test_as_pydantic_type_returns_str():
    assert ExampleColumnType("red", "blue").as_type() is str
