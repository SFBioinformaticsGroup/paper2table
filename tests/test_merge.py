import pytest
from tablemerge.merge import merge_tablesfiles
from tablevalidate.schema import TablesFile, TableWithFragments, TableFragment, Row


def wrap(rows: list[Row], page=1, citation=""):
    return TablesFile(
        tables=[
            TableWithFragments(table_fragments=[TableFragment(rows=rows, page=page)])
        ],
        citation=citation,
    )


def test_empty_tables_list():
    with pytest.raises(ValueError):
        merge_tablesfiles([])


def test_single_table_returns_normalized():
    table = [Row(family=" Apiaceae ", scientific_name="Ammi majus L.")]

    result = merge_tablesfiles([wrap(table)])
    assert len(result.tables) == 1
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.")
    ]


def test_two_identical_tables():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]

    result = merge_tablesfiles([wrap(table), wrap(table)])
    assert len(result.tables) == 1
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.")
    ]


def test_two_tables_with_non_normalized_columns():
    table_1 = [Row(family=" Apiaceae ", scientific_name=" Ammi majus L. ")]
    table_2 = [Row(family="apiaceae", scientific_name="ammi majus l.")]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.")
    ]


def test_two_tables_with_mixed_values():
    table_1 = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    table_2 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
    ]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l."),
        Row(family="rosaceae", scientific_name="rosa canina l."),
    ]


def test_three_tables_with_different_values():
    table_1 = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    table_2 = [Row(family="Rosaceae", scientific_name="Rosa canina L.")]
    table_3 = [Row(family="Lamiaceae", scientific_name="Mentha spicata L.")]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2), wrap(table_3)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l."),
        Row(family="rosaceae", scientific_name="rosa canina l."),
        Row(family="lamiaceae", scientific_name="mentha spicata l."),
    ]


def test_three_tables_with_overlapped_mixed_values():
    table_1 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
    ]
    table_2 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
    ]
    table_3 = [
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
        Row(family="Lamiaceae", scientific_name="Mentha spicata L."),
    ]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2), wrap(table_3)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l."),
        Row(family="rosaceae", scientific_name="rosa canina l."),
        Row(family="lamiaceae", scientific_name="mentha spicata l."),
    ]


def test_three_tables_with_conflicting_values_with_row_agreement_level():
    table_1 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
    ]
    table_2 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
    ]
    table_3 = [
        Row(family="Apiaceae", scientific_name="Ammi"),
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
        Row(family="Lamiaceae", scientific_name="Mentha spicata L."),
    ]

    result = merge_tablesfiles(
        [wrap(table_1), wrap(table_2), wrap(table_3)], with_row_agreement=True
    )
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", _agreement_level=2),
        Row(family="apiaceae", scientific_name="ammi", _agreement_level=1),
        Row(family="rosaceae", scientific_name="rosa canina l.", _agreement_level=2),
        Row(
            family="lamiaceae", scientific_name="mentha spicata l.", _agreement_level=2
        ),
    ]


def test_three_tables_with_conflicting_values_with_column_agreement_level():
    table_1 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
    ]
    table_2 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
    ]
    table_3 = [
        Row(family="Apiaceae", scientific_name="Ammi"),
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
        Row(family="Lamiaceae", scientific_name="Mentha spicata L."),
    ]

    result = merge_tablesfiles(
        [wrap(table_1), wrap(table_2), wrap(table_3)], with_column_agreement=True
    )
    assert result.tables[0].table_fragments[0].rows == [
        Row(
            family="apiaceae",
            scientific_name=[
                {"value": "ammi majus l.", "_agreement_level": 2},
                {"value": "ammi", "_agreement_level": 1},
            ],
        ),
        Row(
            family="rosaceae",
            scientific_name=[{"value": "rosa canina l.", "_agreement_level": 2}],
        ),
        Row(
            family="lamiaceae",
            scientific_name=[{"value": "mentha spicata l.", "_agreement_level": 2}],
        ),
    ]
