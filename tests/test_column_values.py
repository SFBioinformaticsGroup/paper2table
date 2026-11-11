import pytest

from utils.column_values import (
    DEFAULT_NA_VALUES,
    NA_VALUES,
    configure_na_values,
    normalize_column_value,
    parse_na_values,
)


@pytest.fixture(autouse=True)
def restore_default_na_values():
    yield
    configure_na_values(DEFAULT_NA_VALUES)


def test_normalize_column_value_collapses_default_expressions():
    assert normalize_column_value("None") == ""
    assert normalize_column_value("n/a") == ""
    assert normalize_column_value("Not Identified") == ""
    assert normalize_column_value("undetermined") == ""


def test_normalize_column_value_returns_normalized_string_for_unknown_value():
    assert normalize_column_value("Orange") == "orange"


def test_configure_na_values_replaces_defaults_completely():
    configure_na_values(["no observado", "desconocido"])

    assert normalize_column_value("no observado") == ""
    assert normalize_column_value("Desconocido") == ""
    assert normalize_column_value("none") == "none"
    assert normalize_column_value("n/a") == "n/a"


def test_parse_na_values_returns_newline_separated_entries():
    assert parse_na_values("none\nn/a\nno observado") == [
        "none",
        "n/a",
        "no observado",
    ]


def test_parse_na_values_normalizes_entries():
    assert parse_na_values("  No Observado  \nDESCONOCIDO") == [
        "no observado",
        "desconocido",
    ]


def test_parse_na_values_strips_whitespace():
    assert parse_na_values("  none  \n\t n/a \n") == ["none", "n/a"]


def test_parse_na_values_ignores_blank_lines_and_comments():
    text = "\nnone\n\n# a comment line\nno observado\n"
    assert parse_na_values(text) == ["none", "no observado"]
