import pytest
from tablemerge.merge import merge_tablesfiles
from tablevalidate.schema import TablesFile

def wrap_tablesfile(rows, page=1, citation=""):
    table = {"rows": rows, "page": page}
    return TablesFile.model_validate({"tables": [table], "citation": citation})


def test_empty_tables_list():
    with pytest.raises(ValueError):
        merge_tablesfiles([])


def test_single_table_returns_normalized():
    table = [{"family": " Apiaceae ", "scientific_name": "Ammi majus L."}]

    result = merge_tablesfiles([wrap_tablesfile(table)])
    assert len(result) == 1
    assert result[0]["rows"] == [
        {"family": "apiaceae", "scientific_name": "ammi majus l."}
    ]


def test_two_identical_tables():
    table = [{"family": "Apiaceae", "scientific_name": "Ammi majus L."}]

    result = merge_tablesfiles([wrap_tablesfile(table), wrap_tablesfile(table)])
    assert len(result) == 1
    assert result[0]["rows"] == [
        {"family": "apiaceae", "scientific_name": "ammi majus l."}
    ]


def test_two_tables_with_non_normalized_columns():
    table_1 = [{"family": " Apiaceae ", "scientific_name": " Ammi majus L. "}]
    table_2 = [{"family": "apiaceae", "scientific_name": "ammi majus l."}]

    result = merge_tablesfiles([wrap_tablesfile(table_1), wrap_tablesfile(table_2)])
    assert result[0]["rows"] == [
        {"family": "apiaceae", "scientific_name": "ammi majus l."}
    ]


def test_two_tables_with_mixed_values():
    table_1 = [{"family": "Apiaceae", "scientific_name": "Ammi majus L."}]
    table_2 = [
        {"family": "Apiaceae", "scientific_name": "Ammi majus L."},
        {"family": "Rosaceae", "scientific_name": "Rosa canina L."},
    ]

    result = merge_tablesfiles([wrap_tablesfile(table_1), wrap_tablesfile(table_2)])
    assert result[0]["rows"] == [
        {"family": "apiaceae", "scientific_name": "ammi majus l."},
        {"family": "rosaceae", "scientific_name": "rosa canina l."},
    ]


def test_three_tables():
    table_1 = [{"family": "Apiaceae", "scientific_name": "Ammi majus L."}]
    table_2 = [{"family": "Rosaceae", "scientific_name": "Rosa canina L."}]
    table_3 = [{"family": "Lamiaceae", "scientific_name": "Mentha spicata L."}]

    result = merge_tablesfiles(
        [wrap_tablesfile(table_1), wrap_tablesfile(table_2), wrap_tablesfile(table_3)]
    )
    assert result[0]["rows"] == [
        {"family": "apiaceae", "scientific_name": "ammi majus l."},
        {"family": "rosaceae", "scientific_name": "rosa canina l."},
        {"family": "lamiaceae", "scientific_name": "mentha spicata l."},
    ]
