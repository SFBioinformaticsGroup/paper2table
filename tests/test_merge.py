import pytest
from tablemerge.merge import merge_tablesfiles, merge_rows
from tablevalidate.schema import (
    TablesFile,
    TableWithFragments,
    TableFragment,
    Row,
    ValueWithAgreement,
)


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


def test_single_table_with_row_agreement():
    table = [Row(family=" Apiaceae ", scientific_name="Ammi majus L.")]

    result = merge_tablesfiles([wrap(table)], row_agreement=True)
    assert len(result.tables) == 1
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1)
    ]


def test_two_identical_tables():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]

    result = merge_tablesfiles([wrap(table), wrap(table)])
    assert len(result.tables) == 1
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.")
    ]


def test_two_identical_tables_with_row_agreement():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]

    result = merge_tablesfiles([wrap(table), wrap(table)], row_agreement=True)
    assert len(result.tables) == 1
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2)
    ]


def test_two_tables_with_non_normalized_columns():
    table_1 = [Row(family=" Apiaceae ", scientific_name=" Ammi majus L. ")]
    table_2 = [Row(family="apiaceae", scientific_name="ammi majus l.")]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.")
    ]


def test_two_tables_with_different_column_names():
    table_1 = [Row(family=" Apiaceae ", scientific_name=" Ammi majus L. ")]
    table_2 = [Row(**{"0": "apiaceae", "1": "ammi majus l."})]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l."),
        Row(**{"0": "apiaceae", "1": "ammi majus l."}),
    ]


def test_two_tables_with_different_column_names_and_row_agreement():
    table_1 = [Row(family=" Apiaceae ", scientific_name=" Ammi majus L. ")]
    table_2 = [Row(**{"0": "apiaceae", "1": "ammi majus l."})]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2)], with_row_agreement=True)
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1),
        Row(**{"0": "apiaceae", "1": "ammi majus l."}, agreement_level_=1),
    ]


def test_two_tables_with_different_values():
    table_1 = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    table_2 = [
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
    ]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l."),
        Row(family="rosaceae", scientific_name="rosa canina l."),
    ]


def test_two_tablesfiles_with_different_pages():
    table_1 = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    table_2 = [
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
    ]

    result = merge_tablesfiles([wrap(table_1, page=1), wrap(table_2, page=2)])
    assert len(result.tables) == 1

    assert result.tables[0].table_fragments[0].page == 1
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l."),
    ]

    assert result.tables[0].table_fragments[1].page == 2
    assert result.tables[0].table_fragments[1].rows == [
        Row(family="rosaceae", scientific_name="rosa canina l."),
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


def test_three_tables_with_conflicting_values_without_row_agreement_level():
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

    result = merge_tablesfiles([wrap(table_1), wrap(table_2), wrap(table_3)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l."),
        Row(family="apiaceae", scientific_name="ammi"),
        Row(family="rosaceae", scientific_name="rosa canina l."),
        Row(family="lamiaceae", scientific_name="mentha spicata l."),
    ]


def test_two_tables_with_conflicting_values_and_wrong_first_without_row_agreement_level():
    table_1 = [
        Row(family="Apiaceae", scientific_name="Ammi"),
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
        Row(family="Lamiaceae", scientific_name="Mentha spicata L."),
    ]
    table_2 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
    ]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi"),
        Row(family="rosaceae", scientific_name="rosa canina l."),
        Row(family="lamiaceae", scientific_name="mentha spicata l."),
        # TODO add it not at bottom but next to the closest one
        Row(family="apiaceae", scientific_name="ammi majus l."),
    ]


def test_three_tables_with_conflicting_values_and_wrong_first_without_row_agreement_level():
    table_1 = [
        Row(family="Apiaceae", scientific_name="Ammi"),
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
        Row(family="Lamiaceae", scientific_name="Mentha spicata L."),
    ]
    table_2 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
    ]
    table_3 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
    ]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2), wrap(table_3)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi"),
        Row(family="apiaceae", scientific_name="ammi majus l."),
        Row(family="rosaceae", scientific_name="rosa canina l."),
        Row(family="lamiaceae", scientific_name="mentha spicata l."),
    ]


def test_three_tables_with_conflicting_values_and_wrong_in_the_middle_without_row_agreement_level():
    table_1 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
    ]
    table_2 = [
        Row(family="Apiaceae", scientific_name="Ammi"),
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
        Row(family="Lamiaceae", scientific_name="Mentha spicata L."),
    ]
    table_3 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
    ]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2), wrap(table_3)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l."),
        Row(family="apiaceae", scientific_name="ammi"),
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
        [wrap(table_1), wrap(table_2), wrap(table_3)], row_agreement=True
    )
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2),
        Row(family="apiaceae", scientific_name="ammi", agreement_level_=1),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=2),
        Row(
            family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1
        ),
    ]


def xtest_three_tables_with_conflicting_values_with_column_agreement_level():
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
        [wrap(table_1), wrap(table_2), wrap(table_3)], column_agreement=True
    )
    assert result.tables[0].table_fragments[0].rows == [
        Row(
            family="apiaceae",
            scientific_name=[
                ValueWithAgreement("ammi majus l.", 2),
                ValueWithAgreement("ammi", 1),
            ],
        ),
        Row(
            family="rosaceae",
            scientific_name=[ValueWithAgreement("rosa canina l.", 2)],
        ),
        Row(
            family="lamiaceae",
            scientific_name=[ValueWithAgreement("mentha spicata l.", 2)],
        ),
    ]


def test_merge_same_rows_with_column_agreement():
    assert merge_rows(
        Row(
            family="rosaceae",
            scientific_name="rosa canina",
        ),
        Row(
            family="rosaceae",
            scientific_name="rosa canina",
        ),
        column_agreement=True,
    ) == Row(
        family="rosaceae",
        scientific_name=[
            ValueWithAgreement("rosa canina", 2),
        ],
    )


def test_merge_different_rows_with_column_agreement():
    assert merge_rows(
        Row(
            family="rosaceae",
            scientific_name="rosa canina l.",
        ),
        Row(
            family="rosaceae",
            scientific_name="rosa canina",
        ),
        column_agreement=True,
    ) == Row(
        family="rosaceae",
        scientific_name=[
            ValueWithAgreement("rosa canina l.", 1),
            ValueWithAgreement("rosa canina.", 1),
        ],
    )
