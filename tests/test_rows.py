from utils.rows import is_empty_value, is_empty_row


# ── is_empty_value ────────────────────────────────────────────────────────────

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
    assert not is_empty_value([
        {"value": "", "agreement_level": 1},
        {"value": "Apiaceae", "agreement_level": 1},
    ])


# ── is_empty_row (dict form) ──────────────────────────────────────────────────

def test_is_empty_row_all_empty():
    assert is_empty_row({"family": "", "scientific_name": None})


def test_is_empty_row_whitespace_only():
    assert is_empty_row({"family": "  ", "scientific_name": "\t"})


def test_is_empty_row_metadata_keys_ignored():
    assert is_empty_row({"family": "", "agreement_level_": 2, "sources_": ["uuid"]})


def test_is_empty_row_any_key_ending_underscore_ignored():
    assert is_empty_row({"family": "", "custom_meta_": "something"})


def test_is_empty_row_has_data():
    assert not is_empty_row({"family": "Apiaceae", "scientific_name": ""})


def test_is_empty_row_list_value_empty():
    assert is_empty_row({"family": [{"value": "", "agreement_level": 1}]})


def test_is_empty_row_list_value_non_empty():
    assert not is_empty_row({"family": [{"value": "Apiaceae", "agreement_level": 1}]})
