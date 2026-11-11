# pyright: reportCallIssue=false

import pytest

from tablevalidate.schema import Row, ValueWithAgreement
from utils.column_values import DEFAULT_NA_VALUES, configure_na_values


@pytest.fixture(autouse=True)
def restore_default_na_values():
    yield
    configure_na_values(DEFAULT_NA_VALUES)


def test_is_empty_value_true_for_none():
    assert Row.is_empty_value(None) is True


def test_is_empty_value_true_for_empty_string():
    assert Row.is_empty_value("") is True


def test_is_empty_value_true_for_whitespace_only_string():
    assert Row.is_empty_value("   \t\n") is True


def test_is_empty_value_false_for_known_na_value():
    assert Row.is_empty_value("none") is False


def test_is_empty_value_false_for_regular_string():
    assert Row.is_empty_value("orange") is False


def test_is_empty_value_true_for_list_of_blank_values():
    assert (
        Row.is_empty_value(
            [
                ValueWithAgreement(value=None, agreement_level=1),
                ValueWithAgreement(value="", agreement_level=1),
                ValueWithAgreement(value="   ", agreement_level=1),
            ]
        )
        is True
    )


def test_is_empty_value_false_for_list_containing_na_value():
    assert (
        Row.is_empty_value([ValueWithAgreement(value="none", agreement_level=1)])
        is False
    )


def test_is_empty_true_when_all_columns_are_blank():
    assert Row(name="", color=None).is_empty() is True


def test_is_empty_false_when_any_column_is_a_na_value():
    row = Row(name="none", color="")
    assert row.is_empty() is False
    assert row.is_na() is True


def test_is_empty_ignores_metadata_fields():
    assert Row(family="", agreement_level_=2, sources_=["abc"]).is_empty() is True


def test_is_empty_false_when_row_has_data():
    assert Row(family="Apiaceae", scientific_name="").is_empty() is False


def test_is_empty_ignores_custom_na_values():
    configure_na_values(["no observado"])

    row = Row(name="no observado")
    assert row.is_empty() is False
    assert row.is_na() is True
