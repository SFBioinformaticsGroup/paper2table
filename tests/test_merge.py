import pytest
from tablemerge.merge import merge_tables_list


def wrap_table(rows, page=None):
    table = {"rows": rows}
    if page is not None:
        table["page"] = page
    return [table]


def test_empty_tables_list():
    with pytest.raises(ValueError):
        merge_tables_list([])


def test_single_table_returns_normalized():
    table = [{"family": " Apiaceae ", "scientific_name": "Ammi majus L."}]

    result = merge_tables_list([wrap_table(table)])
    assert len(result) == 1
    assert result[0]["rows"] == [
        {"family": "apiaceae", "scientific_name": "ammi majus l."}
    ]


def test_two_identical_tables():
    table = [{"family": "Apiaceae", "scientific_name": "Ammi majus L."}]

    result = merge_tables_list([wrap_table(table), wrap_table(table)])
    assert len(result) == 1
    assert result[0]["rows"] == [
        {"family": "apiaceae", "scientific_name": "ammi majus l."}
    ]


def test_two_tables_with_non_normalized_columns():
    table_1 = [{"family": " Apiaceae ", "scientific_name": " Ammi majus L. "}]
    table_2 = [{"family": "apiaceae", "scientific_name": "ammi majus l."}]

    result = merge_tables_list([wrap_table(table_1), wrap_table(table_2)])
    assert result[0]["rows"] == [
        {"family": "apiaceae", "scientific_name": "ammi majus l."}
    ]


def test_two_tables_with_mixed_values():
    table_1 = [{"family": "Apiaceae", "scientific_name": "Ammi majus L."}]
    table_2 = [
        {"family": "Apiaceae", "scientific_name": "Ammi majus L."},
        {"family": "Rosaceae", "scientific_name": "Rosa canina L."},
    ]

    result = merge_tables_list([wrap_table(table_1), wrap_table(table_2)])
    assert result[0]["rows"] == [
        {"family": "apiaceae", "scientific_name": "ammi majus l."},
        {"family": "rosaceae", "scientific_name": "rosa canina l."},
    ]


def test_three_tables():
    table_1 = [{"family": "Apiaceae", "scientific_name": "Ammi majus L."}]
    table_2 = [{"family": "Rosaceae", "scientific_name": "Rosa canina L."}]
    table_3 = [{"family": "Lamiaceae", "scientific_name": "Mentha spicata L."}]

    result = merge_tables([wrap_table(table_1), wrap_table(table_2), wrap_table(table_3)])
    assert result[0]["rows"] == [
        {"family": "apiaceae", "scientific_name": "ammi majus l."},
        {"family": "rosaceae", "scientific_name": "rosa canina l."},
        {"family": "lamiaceae", "scientific_name": "mentha spicata l."},
    ]
