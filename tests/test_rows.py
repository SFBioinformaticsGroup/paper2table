# pyright: reportCallIssue=false

from utils.rows import is_empty_value, normalize_str_value
from tablevalidate.schema import Row, ValueWithAgreement


def test_normalize_str_value_no_data_lowercase():
    assert normalize_str_value("no data") == ""


def test_normalize_str_value_no_data_uppercase():
    assert normalize_str_value("No Data") == ""


def test_normalize_str_value_no_data_extra_whitespace():
    assert normalize_str_value("  no  data  ") == ""


def test_normalize_str_value_none():
    assert normalize_str_value("None") == ""


def test_normalize_str_value_regular_value():
    assert normalize_str_value("Apiaceae") == "apiaceae"


def test_is_empty_value_no_data_string():
    assert is_empty_value("no data")


def test_is_empty_value_no_data_uppercase():
    assert is_empty_value("No Data")


def test_is_empty_value_none():
    assert is_empty_value(None)


def test_is_empty_value_empty_string():
    assert is_empty_value("")


def test_is_empty_value_whitespace_string():
    assert is_empty_value("  \t\n")


def test_is_empty_value_non_empty_string():
    assert not is_empty_value("hello")


def test_is_empty_value_list_of_dicts_empty():
    assert is_empty_value([{"value": "", "agreement_level": 1}])


def test_is_empty_value_list_of_dicts_whitespace():
    assert is_empty_value([{"value": "  ", "agreement_level": 1}])


def test_is_empty_value_list_of_dicts_non_empty():
    assert not is_empty_value([{"value": "Apiaceae", "agreement_level": 1}])


def test_is_empty_value_list_mixed_empty_and_non_empty():
    assert not is_empty_value(
        [
            {"value": "", "agreement_level": 1},
            {"value": "Apiaceae", "agreement_level": 1},
        ]
    )


def test_is_empty_row_all_empty():
    assert Row(family="", scientific_name=None).is_empty()


def test_is_empty_row_whitespace_only():
    assert Row(family="  ", scientific_name="\t").is_empty()


def test_is_empty_row_metadata_keys_ignored():
    assert Row(family="", agreement_level_=2, sources_=["uuid"]).is_empty()


def test_is_empty_row_has_data():
    assert not Row(family="Apiaceae", scientific_name="").is_empty()


def test_is_empty_row_list_value_empty():
    assert Row(family=[ValueWithAgreement(value="", agreement_level=1)]).is_empty()


def test_is_empty_row_list_value_non_empty():
    assert not Row(
        family=[ValueWithAgreement(value="Apiaceae", agreement_level=1)]
    ).is_empty()
