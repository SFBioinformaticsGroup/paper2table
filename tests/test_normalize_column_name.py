from utils.column_names import normalize_column_name


def test_normalize_column_name_spaces_become_underscores():
    assert normalize_column_name("Utilized part") == "utilized_part"


def test_normalize_column_name_uppercase():
    assert normalize_column_name("UTILIZED PART") == "utilized_part"


def test_normalize_column_name_mixed_case():
    assert normalize_column_name("Utilized Part") == "utilized_part"


def test_normalize_column_name_accent():
    assert normalize_column_name("Preparación") == "preparacion"


def test_normalize_column_name_already_normalized():
    assert normalize_column_name("utilized_part") == "utilized_part"


def test_normalize_column_name_none_returns_none():
    assert normalize_column_name(None) is None
