# pyright: reportCallIssue=false
# pyright: reportArgumentType=false
import pytest
from tablemerge.__main__ import group_tablesfiles, filter_groups_by_paper
from tablemerge.analyzers import JaccardAnalyzer, AliasAnalyzer
from tablemerge.merge import (
    filter_semantic_columns,
    filter_header_rows,
    filter_title_rows,
    drop_empty_non_semantic_columns,
    drop_empty_tables,
    is_title_row,
    is_header_row,
    has_semantic_header_value,
    has_hints_header_value,
    value_matches_header,
    value_matches_hints,
)
from tablemerge.agreement import SimpleCountAgreement, DistinctReadersAgreement
from tablemerge.fragments_builder import merge_rows, to_values_with_agreement
from tablemerge.tablesfile_merger import merge_tablesfiles
from tablevalidate.schema import (
    TablesFile,
    TableWithFragments,
    TableFragment,
    Row,
    ValueWithAgreement,
)


def wrap(rows: list[Row], page=1, citation="", uuid=None):
    return TablesFile(
        tables=[
            TableWithFragments(table_fragments=[TableFragment(rows=rows, page=page)])
        ],
        citation=citation,
        uuid=uuid,
    )


def test_empty_tables_list():
    with pytest.raises(ValueError):
        merge_tablesfiles([])


def test_single_table_returns_normalized():
    table = [Row(family=" Apiaceae ", scientific_name="Ammi majus L.")]

    result = merge_tablesfiles([wrap(table)])
    assert len(result.tables) == 1
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1, row_=0)
    ]


def test_single_table_with_row_agreement():
    table = [Row(family=" Apiaceae ", scientific_name="Ammi majus L.")]

    result = merge_tablesfiles([wrap(table)], agreement=SimpleCountAgreement())
    assert len(result.tables) == 1
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1, row_=0)
    ]


def test_two_identical_tables():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]

    result = merge_tablesfiles([wrap(table), wrap(table)])
    assert len(result.tables) == 1
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2, row_=0)
    ]


def test_two_identical_tables_with_row_agreement():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]

    result = merge_tablesfiles(
        [wrap(table), wrap(table)], agreement=SimpleCountAgreement()
    )
    assert len(result.tables) == 1
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2, row_=0)
    ]


def test_two_tables_with_non_normalized_columns():
    table_1 = [Row(family=" Apiaceae ", scientific_name=" Ammi majus L. ")]
    table_2 = [Row(family="apiaceae", scientific_name="ammi majus l.")]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2, row_=0)
    ]


def test_two_tables_with_different_column_names_and_alignment():
    table_1 = [Row(family=" Apiaceae ", scientific_name=" Ammi majus L. ")]
    table_2 = [Row(**{"0": "apiaceae", "1": "ammi majus l."})]

    result = merge_tablesfiles(
        [wrap(table_1), wrap(table_2)], analyzers=[JaccardAnalyzer()]
    )
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2, row_=0),
    ]


def test_two_tables_with_different_column_names_and_no_alignment():
    table_1 = [Row(family=" Apiaceae ", scientific_name=" Ammi majus L. ")]
    table_2 = [Row(**{"0": "apiaceae", "1": "ammi majus l."})]

    result = merge_tablesfiles(
        [wrap(table_1), wrap(table_2)], agreement=SimpleCountAgreement()
    )
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1, row_=0),
        Row(
            agreement_level_=1, sources_=None, row_=0, **{"0": "apiaceae", "1": "ammi majus l."}
        ),
    ]


def test_two_tables_with_different_values():
    table_1 = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    table_2 = [
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
    ]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1, row_=0),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=1, row_=0),
    ]


def test_two_tablesfiles_with_different_pages():
    table_1 = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    table_2 = [
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
    ]

    result = merge_tablesfiles([wrap(table_1, page=1), wrap(table_2, page=2)])
    assert len(result.tables) == 1

    assert result.tables[0].get_table_fragments()[0].page == 1
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1, row_=0),
    ]

    assert result.tables[0].get_table_fragments()[1].page == 2
    assert result.tables[0].get_table_fragments()[1].rows == [
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=1, row_=0),
    ]


def test_two_tables_with_mixed_values():
    table_1 = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    table_2 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
    ]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2, row_=0),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=1, row_=1),
    ]


def test_three_tables_with_different_values():
    table_1 = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    table_2 = [Row(family="Rosaceae", scientific_name="Rosa canina L.")]
    table_3 = [Row(family="Lamiaceae", scientific_name="Mentha spicata L.")]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2), wrap(table_3)])
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1, row_=0),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=1, row_=0),
        Row(family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1, row_=0),
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
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2, row_=0),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=1, row_=0),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=1, row_=1),
        Row(family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1, row_=1),
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
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2, row_=0),
        Row(family="apiaceae", scientific_name="ammi", agreement_level_=1, row_=0),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=2, row_=1),
        Row(family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1, row_=2),
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
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi", agreement_level_=1, row_=0),
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1, row_=0),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=1, row_=1),
        Row(family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1, row_=2),
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
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi", agreement_level_=1, row_=0),
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2, row_=0),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=2, row_=1),
        Row(family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1, row_=2),
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
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2, row_=0),
        Row(family="apiaceae", scientific_name="ammi", agreement_level_=1, row_=0),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=2, row_=1),
        Row(family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1, row_=2),
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
        [wrap(table_1), wrap(table_2), wrap(table_3)], agreement=SimpleCountAgreement()
    )
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2, row_=0),
        Row(family="apiaceae", scientific_name="ammi", agreement_level_=1, row_=0),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=2, row_=1),
        Row(family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1, row_=2),
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
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(
            family="apiaceae",
            scientific_name=[
                ValueWithAgreement(value="ammi majus l.", agreement_level=2),
                ValueWithAgreement(value="ammi", agreement_level=1),
            ],
        ),
        Row(
            family="rosaceae",
            scientific_name=[
                ValueWithAgreement(value="rosa canina l.", agreement_level=2)
            ],
        ),
        Row(
            family="lamiaceae",
            scientific_name=[
                ValueWithAgreement(value="mentha spicata l.", agreement_level=2)
            ],
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
        family=[ValueWithAgreement(value="rosaceae", agreement_level=2)],
        scientific_name=[
            ValueWithAgreement(value="rosa canina", agreement_level=2),
        ],
        agreement_level_=2,
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
        family=[ValueWithAgreement(value="rosaceae", agreement_level=2)],
        scientific_name=[
            ValueWithAgreement(value="rosa canina l.", agreement_level=1),
            ValueWithAgreement(value="rosa canina", agreement_level=1),
        ],
        agreement_level_=2,
    )


def test_sources_stamped_on_single_tablesfile():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    result = merge_tablesfiles([wrap(table, uuid="uuid-a")])
    rows = result.tables[0].get_table_fragments()[0].rows
    assert rows[0].sources_ == ["uuid-a"]


def test_sources_merged_on_matched_rows():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    result = merge_tablesfiles([wrap(table, uuid="uuid-a"), wrap(table, uuid="uuid-b")])
    rows = result.tables[0].get_table_fragments()[0].rows
    assert rows[0].sources_ == ["uuid-a", "uuid-b"]


def test_sources_only_left_uuid_on_unmatched_left_row():
    table_1 = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    table_2 = [Row(family="Rosaceae", scientific_name="Rosa canina L.")]
    result = merge_tablesfiles(
        [wrap(table_1, uuid="uuid-a"), wrap(table_2, uuid="uuid-b")]
    )
    rows = result.tables[0].get_table_fragments()[0].rows
    assert rows[0].sources_ == ["uuid-a"]
    assert rows[1].sources_ == ["uuid-b"]


def test_sources_right_uuid_on_skipped_row():
    table_1 = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    table_2 = [
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
    ]
    result = merge_tablesfiles(
        [wrap(table_1, uuid="uuid-a"), wrap(table_2, uuid="uuid-b")]
    )
    rows = result.tables[0].get_table_fragments()[0].rows
    # With position-aware merge: left Apiaceae is at row_=0, right Rosaceae is at row_=0 (no match),
    # right Apiaceae is at row_=1 (different position from left row_=0, so no merge either).
    assert rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1, sources_=["uuid-a"], row_=0),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=1, sources_=["uuid-b"], row_=0),
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1, sources_=["uuid-b"], row_=1),
    ]


def test_two_tables_with_unicode_variant_values():
    # look the same but are different ñ
    table_1 = [Row(common_name="pezuña de vaca")]
    table_2 = [Row(common_name="pezuña de vaca")]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(common_name="pezuña de vaca", agreement_level_=2, row_=0)
    ]


def test_sources_deduped_when_same_uuid_appears_twice():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    result = merge_tablesfiles([wrap(table, uuid="uuid-a"), wrap(table, uuid="uuid-a")])
    rows = result.tables[0].get_table_fragments()[0].rows
    assert rows[0].sources_ == ["uuid-a"]


def test_sources_none_when_no_uuid_on_tablesfiles():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    result = merge_tablesfiles([wrap(table), wrap(table)])
    rows = result.tables[0].get_table_fragments()[0].rows
    assert rows[0].sources_ is None


def test_merge_different_rows_that_already_have_agreement_with_column_agreement():
    assert merge_rows(
        Row(
            family=[ValueWithAgreement(value="rosaceae", agreement_level=2)],
            scientific_name=[
                ValueWithAgreement(value="rosa canina l.", agreement_level=1),
                ValueWithAgreement(value="rosa canina", agreement_level=1),
            ],
        ),
        Row(
            family="rosaceae",
            scientific_name="rosa canina",
        ),
        column_agreement=True,
    ) == Row(
        family=[ValueWithAgreement(value="rosaceae", agreement_level=3)],
        scientific_name=[
            ValueWithAgreement(value="rosa canina l.", agreement_level=1),
            ValueWithAgreement(value="rosa canina", agreement_level=2),
        ],
        agreement_level_=2,
    )


def test_is_empty_row_all_empty_strings():
    assert Row(family="", scientific_name="").is_empty()


def test_is_empty_row_whitespace_only():
    assert Row(family="  ", scientific_name="\t").is_empty()


def test_is_empty_row_none_values():
    assert Row(family=None, scientific_name=None).is_empty()


def test_is_empty_row_metadata_fields_ignored():
    assert Row(family="", agreement_level_=2, sources_=["abc"]).is_empty()


def test_is_empty_row_not_empty_when_has_data():
    assert not Row(family="Apiaceae", scientific_name="").is_empty()


def test_is_empty_row_value_with_agreement_all_empty():
    assert Row(family=[ValueWithAgreement(value="", agreement_level=1)]).is_empty()


def test_is_empty_row_value_with_agreement_has_data():
    assert not Row(
        family=[ValueWithAgreement(value="Apiaceae", agreement_level=1)]
    ).is_empty()


def test_merge_filters_empty_rows_from_single_table():
    table = [
        Row(family="Apiaceae", scientific_name=""),
        Row(family="", scientific_name=""),
    ]
    result = merge_tablesfiles([wrap(table)])
    rows = result.tables[0].get_table_fragments()[0].rows
    assert len(rows) == 1
    assert rows[0].family == "apiaceae"


def test_merge_filters_whitespace_only_rows():
    table = [
        Row(family="  ", scientific_name="\n"),
        Row(family="Rosaceae", scientific_name="Rosa"),
    ]
    result = merge_tablesfiles([wrap(table)])
    rows = result.tables[0].get_table_fragments()[0].rows
    assert len(rows) == 1
    assert rows[0].family == "rosaceae"


def test_merge_filters_empty_rows_from_two_tables():
    table_1 = [Row(family="Apiaceae"), Row(family="")]
    table_2 = [Row(family="Apiaceae"), Row(family="")]
    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    rows = result.tables[0].get_table_fragments()[0].rows
    assert len(rows) == 1
    assert rows[0].family == "apiaceae"


def test_merge_keeps_rows_with_partial_data():
    table = [
        Row(family="Apiaceae", scientific_name=""),
        Row(family="", scientific_name=""),
    ]
    result = merge_tablesfiles([wrap(table)])
    rows = result.tables[0].get_table_fragments()[0].rows
    assert len(rows) == 1


def test_is_semantic_column():
    assert not Row.is_semantic_column("1")
    assert not Row.is_semantic_column("2023")
    assert not Row.is_semantic_column("3.14")
    assert not Row.is_semantic_column("-5")
    assert Row.is_semantic_column("family")
    assert Row.is_semantic_column("1a")
    assert Row.is_semantic_column("")


def test_filter_semantic_columns_removes_numeric():
    table = [Row(**{"family": "Apiaceae", "1": "yes", "2023": "data"})]
    result = merge_tablesfiles([wrap(table)])
    filtered = filter_semantic_columns(result)
    rows = filtered.tables[0].get_table_fragments()[0].rows
    assert len(rows) == 1
    assert rows[0].get_columns() == {"family": "apiaceae"}


def test_filter_semantic_columns_keeps_all_if_no_numeric():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus")]
    result = merge_tablesfiles([wrap(table)])
    filtered = filter_semantic_columns(result)
    rows = filtered.tables[0].get_table_fragments()[0].rows
    assert len(rows) == 1
    assert set(rows[0].get_columns().keys()) == {"family", "scientific_name"}


def test_drop_empty_non_semantic_columns_removes_all_null_column():
    table = [
        Row(**{"family": "Apiaceae", "0": None, "1": "value"}),
        Row(**{"family": "Rosaceae", "0": None, "1": "other"}),
    ]
    result = merge_tablesfiles([wrap(table)])
    dropped = drop_empty_non_semantic_columns(result)
    rows = dropped.tables[0].get_table_fragments()[0].rows
    assert rows == [
        Row(family="apiaceae", **{"1": "value"}, agreement_level_=1, row_=0),
        Row(family="rosaceae", **{"1": "other"}, agreement_level_=1, row_=1),
    ]


def test_drop_empty_non_semantic_columns_keeps_column_with_any_value():
    table = [
        Row(**{"family": "Apiaceae", "0": None}),
        Row(**{"family": "Rosaceae", "0": "has_value"}),
    ]
    result = merge_tablesfiles([wrap(table)])
    dropped = drop_empty_non_semantic_columns(result)
    rows = dropped.tables[0].get_table_fragments()[0].rows
    assert rows == [
        Row(family="apiaceae", **{"0": None}, agreement_level_=1, row_=0),
        Row(family="rosaceae", **{"0": "has_value"}, agreement_level_=1, row_=1),
    ]


def test_drop_empty_non_semantic_columns_does_not_touch_semantic_columns():
    table = [Row(family=None, scientific_name="Ammi majus")]
    result = merge_tablesfiles([wrap(table)])
    dropped = drop_empty_non_semantic_columns(result)
    rows = dropped.tables[0].get_table_fragments()[0].rows
    assert rows == [Row(family=None, scientific_name="ammi majus", agreement_level_=1, row_=0)]


def test_is_title_row_detects_figure_prefix():
    assert is_title_row(Row(**{"0": "Figure 1. Species table"}))


def test_is_title_row_detects_fig_dot_prefix():
    assert is_title_row(Row(**{"0": "Fig.3 caption"}))


def test_is_title_row_detects_fig_dot_with_space():
    assert is_title_row(Row(**{"0": "fig. 2"}))


def test_is_title_row_detects_table_prefix():
    assert is_title_row(Row(**{"0": "TABLE 3"}))


def test_is_title_row_detects_figura_prefix():
    assert is_title_row(Row(**{"0": "Figura 2. Tabla de especies"}))


def test_is_title_row_detects_tabla_prefix():
    assert is_title_row(Row(**{"0": "tabla 5"}))


def test_is_title_row_false_when_multiple_non_empty_columns():
    assert not is_title_row(Row(**{"0": "Figure 1", "1": "something"}))


def test_is_title_row_false_when_value_does_not_match():
    assert not is_title_row(Row(**{"0": "Apiaceae"}))


def test_filter_title_rows_removes_title_in_first_three_rows():
    table = [
        Row(**{"0": "Figure 1. Species"}),
        Row(**{"0": "species", "1": "family"}),
        Row(**{"0": "Ammi majus", "1": "Apiaceae"}),
    ]
    result = filter_title_rows(wrap(table))
    rows = result.tables[0].get_table_fragments()[0].rows
    assert rows == [
        Row(**{"0": "species", "1": "family"}),
        Row(**{"0": "Ammi majus", "1": "Apiaceae"}),
    ]


def test_filter_title_rows_does_not_remove_title_after_first_three_rows():
    table = [
        Row(**{"0": "species", "1": "family"}),
        Row(**{"0": "Ammi majus", "1": "Apiaceae"}),
        Row(**{"0": "Rosa canina", "1": "Rosaceae"}),
        Row(**{"0": "Figure 2. Continued"}),
    ]
    result = filter_title_rows(wrap(table))
    rows = result.tables[0].get_table_fragments()[0].rows
    assert rows == [
        Row(**{"0": "species", "1": "family"}),
        Row(**{"0": "Ammi majus", "1": "Apiaceae"}),
        Row(**{"0": "Rosa canina", "1": "Rosaceae"}),
        Row(**{"0": "Figure 2. Continued"}),
    ]


def test_distinct_readers_agreement_two_different_non_agent_readers():
    agreement = DistinctReadersAgreement({"uuid-1": "pdfplumber", "uuid-2": "camelot"})
    left = Row(family="apiaceae", sources_=["uuid-1"])
    right = Row(family="apiaceae", sources_=["uuid-2"])
    assert agreement.calculate_level(left, right) == 2


def test_distinct_readers_agreement_same_non_agent_reader():
    agreement = DistinctReadersAgreement(
        {"uuid-1": "pdfplumber", "uuid-2": "pdfplumber"}
    )
    left = Row(family="apiaceae", sources_=["uuid-1"])
    right = Row(family="apiaceae", sources_=["uuid-2"])
    assert agreement.calculate_level(left, right) == 1


def test_distinct_readers_agreement_two_agent_readers():
    agreement = DistinctReadersAgreement({"uuid-1": "gemini", "uuid-2": "openai"})
    left = Row(family="apiaceae", sources_=["uuid-1"])
    right = Row(family="apiaceae", sources_=["uuid-2"])
    assert agreement.calculate_level(left, right) == 2


def test_distinct_readers_agreement_agent_and_non_agent():
    agreement = DistinctReadersAgreement({"uuid-1": "pdfplumber", "uuid-2": "gemini"})
    left = Row(family="apiaceae", sources_=["uuid-1"])
    right = Row(family="apiaceae", sources_=["uuid-2"])
    assert agreement.calculate_level(left, right) == 2


def test_distinct_readers_agreement_no_sources():
    agreement = DistinctReadersAgreement({})
    left = Row(family="apiaceae")
    right = Row(family="apiaceae")
    assert agreement.calculate_level(left, right) == 1


def test_distinct_readers_agreement_unknown_uuid_counts_as_agent():
    agreement = DistinctReadersAgreement({})
    left = Row(family="apiaceae", sources_=["unknown-uuid"])
    right = Row(family="apiaceae")
    assert agreement.calculate_level(left, right) == 1


def test_merge_two_tables_distinct_non_agent_readers():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    agreement = DistinctReadersAgreement({"uuid-1": "pdfplumber", "uuid-2": "camelot"})
    result = merge_tablesfiles(
        [wrap(table, uuid="uuid-1"), wrap(table, uuid="uuid-2")],
        agreement=agreement,
    )
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(
            family="apiaceae",
            scientific_name="ammi majus l.",
            agreement_level_=2,
            sources_=["uuid-1", "uuid-2"],
            row_=0,
        )
    ]


def test_merge_two_tables_same_non_agent_reader():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    agreement = DistinctReadersAgreement(
        {"uuid-1": "pdfplumber", "uuid-2": "pdfplumber"}
    )
    result = merge_tablesfiles(
        [wrap(table, uuid="uuid-1"), wrap(table, uuid="uuid-2")],
        agreement=agreement,
    )
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(
            family="apiaceae",
            scientific_name="ammi majus l.",
            agreement_level_=1,
            sources_=["uuid-1", "uuid-2"],
            row_=0,
        )
    ]


def test_merge_two_tables_agent_and_non_agent_reader():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    agreement = DistinctReadersAgreement({"uuid-1": "pdfplumber", "uuid-2": "gemini"})
    result = merge_tablesfiles(
        [wrap(table, uuid="uuid-1"), wrap(table, uuid="uuid-2")],
        agreement=agreement,
    )
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(
            family="apiaceae",
            scientific_name="ammi majus l.",
            agreement_level_=2,
            sources_=["uuid-1", "uuid-2"],
            row_=0,
        )
    ]


def test_merge_aligns_right_numeric_columns_multiple_rows():
    table_1 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
        Row(family="Lamiaceae", scientific_name="Mentha spicata L."),
    ]
    table_2 = [
        Row(**{"0": "Apiaceae", "1": "Ammi majus L."}),
        Row(**{"0": "Rosaceae", "1": "Rosa canina L."}),
        Row(**{"0": "Betulaceae", "1": "Betula pendula L."}),
    ]
    result = merge_tablesfiles(
        [wrap(table_1), wrap(table_2)], analyzers=[JaccardAnalyzer()]
    )
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2, row_=0),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=2, row_=1),
        Row(family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1, row_=2),
        Row(family="betulaceae", scientific_name="betula pendula l.", agreement_level_=1, row_=2),
    ]


def test_merge_aligns_right_numeric_columns_with_agreement_multiple_rows():
    table_1 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
        Row(family="Lamiaceae", scientific_name="Mentha spicata L."),
    ]
    table_2 = [
        Row(**{"0": "Apiaceae", "1": "Ammi majus L."}),
        Row(**{"0": "Rosaceae", "1": "Rosa canina L."}),
        Row(**{"0": "Betulaceae", "1": "Betula pendula L."}),
    ]
    result = merge_tablesfiles(
        [wrap(table_1), wrap(table_2)],
        agreement=SimpleCountAgreement(),
        analyzers=[JaccardAnalyzer()],
    )
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2, row_=0),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=2, row_=1),
        Row(family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1, row_=2),
        Row(family="betulaceae", scientific_name="betula pendula l.", agreement_level_=1, row_=2),
    ]


def test_merge_aligns_left_numeric_columns_multiple_rows():
    table_1 = [
        Row(**{"0": "Apiaceae", "1": "Ammi majus L."}),
        Row(**{"0": "Rosaceae", "1": "Rosa canina L."}),
        Row(**{"0": "Betulaceae", "1": "Betula pendula L."}),
    ]
    table_2 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
        Row(family="Lamiaceae", scientific_name="Mentha spicata L."),
    ]
    result = merge_tablesfiles(
        [wrap(table_1), wrap(table_2)], analyzers=[JaccardAnalyzer()]
    )
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2, row_=0),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=2, row_=1),
        Row(family="betulaceae", scientific_name="betula pendula l.", agreement_level_=1, row_=2),
        Row(family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1, row_=2),
    ]


def test_merge_no_alignment_both_semantic_multiple_rows():
    table_1 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
    ]
    table_2 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
        Row(family="Lamiaceae", scientific_name="Mentha spicata L."),
    ]
    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].get_table_fragments()[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2, row_=0),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=1, row_=1),
        Row(family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1, row_=1),
    ]


def test_is_header_row_all_values_match_columns():
    assert is_header_row(Row(family="family", scientific_name="scientific_name"))


def test_is_header_row_case_insensitive():
    assert is_header_row(Row(family="Family", scientific_name="Scientific_Name"))


def test_is_header_row_with_extra_whitespace():
    assert is_header_row(Row(family="  family  ", scientific_name=" scientific_name "))


def test_is_header_row_true_when_one_value_matches():
    assert is_header_row(Row(family="Apiaceae", scientific_name="scientific_name"))


def test_is_header_row_false_when_no_value_matches():
    assert not is_header_row(Row(family="Apiaceae", scientific_name="Ammi majus L."))


def test_is_header_row_false_when_only_numeric_column_matches():
    assert not is_header_row(Row(**{"0": "0", "1": "1"}))


def test_is_header_row_true_when_semantic_column_matches_alongside_numeric():
    assert is_header_row(Row(**{"0": "0", "family": "family"}))


def test_is_header_row_false_when_all_empty():
    assert not is_header_row(Row(family="", scientific_name=""))


def test_is_header_row_with_empty_cells_ignores_them():
    assert is_header_row(Row(family="family", scientific_name=""))


def test_is_header_row_value_with_agreement_matches():
    assert is_header_row(
        Row(family=[ValueWithAgreement(value="family", agreement_level=1)])
    )


def test_is_header_row_value_with_agreement_does_not_match():
    assert not is_header_row(
        Row(family=[ValueWithAgreement(value="Apiaceae", agreement_level=1)])
    )


def test_is_header_row_value_with_agreement_all_empty():
    assert not is_header_row(
        Row(family=[ValueWithAgreement(value="", agreement_level=1)])
    )


def test_filter_header_rows_removes_header_row():
    table = [
        Row(family="family", scientific_name="scientific_name"),
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
    ]
    result = merge_tablesfiles([wrap(table)])
    filtered = filter_header_rows(result)
    rows = filtered.tables[0].get_table_fragments()[0].rows
    assert rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1, row_=1)
    ]


def test_filter_header_rows_keeps_data_rows():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    result = merge_tablesfiles([wrap(table)])
    filtered = filter_header_rows(result)
    rows = filtered.tables[0].get_table_fragments()[0].rows
    assert rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1, row_=0)
    ]


def test_filter_header_rows_with_partial_empty_cells():
    table = [
        Row(family="family", scientific_name=""),
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
    ]
    result = merge_tablesfiles([wrap(table)])
    filtered = filter_header_rows(result)
    rows = filtered.tables[0].get_table_fragments()[0].rows
    assert rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1, row_=1)
    ]


def test_filter_header_rows_removes_row_when_semantic_column_matches_alongside_non_matching_numeric():
    table = [
        Row(**{"family": "family", "scientific_name": "Ammi majus", "0": "some_value"}),
        Row(**{"family": "Apiaceae", "scientific_name": "Ammi majus L.", "0": "123"}),
    ]
    result = merge_tablesfiles([wrap(table)])
    filtered = filter_header_rows(result)
    rows = filtered.tables[0].get_table_fragments()[0].rows
    assert rows == [
        Row(
            **{"family": "apiaceae", "scientific_name": "ammi majus l.", "0": "123"},
            agreement_level_=1,
            row_=1,
        )
    ]


def test_filter_header_rows_preserves_citation_and_metadata():
    table = [Row(family="Apiaceae")]
    tablesfile = wrap(table, citation="some citation")
    result = merge_tablesfiles([tablesfile])
    filtered = filter_header_rows(result)
    assert filtered.citation == "some citation"


def test_normalize_citation_none():
    assert TablesFile.normalize_citation(None) is None


def test_normalize_citation_str_collapses_whitespace():
    assert TablesFile.normalize_citation("Perez  et  al.  2020") == "Perez et al. 2020"


def test_normalize_citation_str_strips_edges():
    assert TablesFile.normalize_citation("  Perez 2020  ") == "Perez 2020"


def test_normalize_citation_str_en_dash():
    assert TablesFile.normalize_citation("Perez–Vílchez, 2020") == "Perez-Vílchez, 2020"


def test_normalize_citation_str_em_dash():
    assert TablesFile.normalize_citation("Perez—Vílchez, 2020") == "Perez-Vílchez, 2020"


def test_normalize_citation_str_preserves_case():
    assert TablesFile.normalize_citation("Perez Et Al. 2020") == "Perez Et Al. 2020"


def test_normalize_citation_list():
    citation = [
        ValueWithAgreement(value="Perez  2020", agreement_level=2),
        ValueWithAgreement(value="Vílchez–Lopez 2021", agreement_level=1),
    ]
    assert TablesFile.normalize_citation(citation) == [
        ValueWithAgreement(value="Perez 2020", agreement_level=2),
        ValueWithAgreement(value="Vílchez-Lopez 2021", agreement_level=1),
    ]


def test_merge_tablesfiles_normalizes_citation_whitespace():
    tablesfile = wrap([Row(family="Apiaceae")], citation="Perez  et  al.  2020")
    result = merge_tablesfiles([tablesfile])
    assert result.citation == "Perez et al. 2020"


def test_merge_tablesfiles_normalizes_citation_dashes():
    tablesfile = wrap([Row(family="Apiaceae")], citation="Perez–Vílchez, 2020")
    result = merge_tablesfiles([tablesfile])
    assert result.citation == "Perez-Vílchez, 2020"


def test_alias_applies_with_single_tablesfile():
    table = [Row(familia="Apiaceae", scientific_name="Ammi majus L.")]
    result = merge_tablesfiles(
        [wrap(table)], analyzers=[AliasAnalyzer({"familia": "family"})]
    )
    rows = result.tables[0].get_table_fragments()[0].rows
    assert rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1, row_=0)
    ]


def test_alias_applies_to_left_only_page_in_multi_file_merge():
    # File A has page 1; file B has page 2 only. Page 1 has no right counterpart.
    # The alias should still be applied to the left-only page 1 fragment.
    table_a = [Row(familia="Apiaceae", scientific_name="Ammi majus L.")]
    table_b = [Row(family="Rosaceae", scientific_name="Rosa canina L.")]
    result = merge_tablesfiles(
        [wrap(table_a, page=1), wrap(table_b, page=2)],
        analyzers=[AliasAnalyzer({"familia": "family"})],
    )
    page1_rows = result.tables[0].get_table_fragments()[0].rows
    assert page1_rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1, row_=0)
    ]


def test_sources_correct_when_middle_tablesfile_is_on_different_page():
    # File A and C share page 1 with matching rows; file B is on page 2.
    # The bug: make_fragments_clusters groups fragments by page and skips files
    # that don't have that page, causing zip(fragments_cluster[1:], tablesfiles[1:])
    # to misalign - C's fragment (index 1 in cluster) is paired with B's tablesfile,
    # and B's fragment (sole entry on page 2) is attributed to tablesfiles[0].uuid.
    row = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    other_row = [Row(family="Rosaceae", scientific_name="Rosa canina L.")]

    result = merge_tablesfiles(
        [
            wrap(row, page=1, uuid="uuid-a"),
            wrap(other_row, page=2, uuid="uuid-b"),
            wrap(row, page=1, uuid="uuid-c"),
        ]
    )

    page1_rows = result.tables[0].get_table_fragments()[0].rows
    assert page1_rows == [
        Row(
            family="apiaceae",
            scientific_name="ammi majus l.",
            agreement_level_=2,
            sources_=["uuid-a", "uuid-c"],
            row_=0,
        )
    ]

    page2_rows = result.tables[0].get_table_fragments()[1].rows
    assert page2_rows == [
        Row(
            family="rosaceae",
            scientific_name="rosa canina l.",
            agreement_level_=1,
            sources_=["uuid-b"],
            row_=0,
        )
    ]


def test_group_tablesfiles_no_aliases(tmp_path):
    dir_a = tmp_path / "a"
    dir_a.mkdir()
    (dir_a / "paper.tables.json").write_text("{}")
    (dir_a / "other.tables.json").write_text("{}")

    assert group_tablesfiles([str(dir_a)], {}) == {
        "paper.tables.json": [(str(dir_a), "paper.tables.json")],
        "other.tables.json": [(str(dir_a), "other.tables.json")],
    }


def test_group_tablesfiles_alias_maps_to_canonical(tmp_path):
    dir_a = tmp_path / "a"
    dir_a.mkdir()
    (dir_a / "paper_v1.tables.json").write_text("{}")

    assert group_tablesfiles([str(dir_a)], {"paper_v1": "paper"}) == {
        "paper.tables.json": [(str(dir_a), "paper_v1.tables.json")],
    }


def test_group_tablesfiles_merges_alias_and_canonical_across_dirs(tmp_path):
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    (dir_a / "paper_v1.tables.json").write_text("{}")
    (dir_b / "paper.tables.json").write_text("{}")

    assert group_tablesfiles([str(dir_a), str(dir_b)], {"paper_v1": "paper"}) == {
        "paper.tables.json": [
            (str(dir_a), "paper_v1.tables.json"),
            (str(dir_b), "paper.tables.json"),
        ],
    }


def test_group_tablesfiles_mixed_aliased_and_plain(tmp_path):
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()
    (dir_a / "paper_v1.tables.json").write_text("{}")
    (dir_b / "paper.tables.json").write_text("{}")
    (dir_b / "report.tables.json").write_text("{}")

    assert group_tablesfiles([str(dir_a), str(dir_b)], {"paper_v1": "paper"}) == {
        "paper.tables.json": [
            (str(dir_a), "paper_v1.tables.json"),
            (str(dir_b), "paper.tables.json"),
        ],
        "report.tables.json": [
            (str(dir_b), "report.tables.json"),
        ],
    }


def test_group_tablesfiles_ignores_non_tablesfile(tmp_path):
    dir_a = tmp_path / "a"
    dir_a.mkdir()
    (dir_a / "paper.tables.json").write_text("{}")
    (dir_a / "tables.metadata.json").write_text("{}")
    (dir_a / "notes.txt").write_text("ignored")

    assert group_tablesfiles([str(dir_a)], {}) == {
        "paper.tables.json": [(str(dir_a), "paper.tables.json")],
    }


def test_filter_groups_by_paper_stem():
    groups = {
        "foo.tables.json": [("dir_a", "foo.tables.json")],
        "bar.tables.json": [("dir_a", "bar.tables.json")],
    }
    assert filter_groups_by_paper(groups, "foo") == {
        "foo.tables.json": [("dir_a", "foo.tables.json")],
    }


def test_filter_groups_by_paper_full_name():
    groups = {
        "foo.tables.json": [("dir_a", "foo.tables.json")],
        "bar.tables.json": [("dir_a", "bar.tables.json")],
    }
    assert filter_groups_by_paper(groups, "foo.tables.json") == {
        "foo.tables.json": [("dir_a", "foo.tables.json")],
    }


def test_filter_groups_by_paper_no_match():
    groups = {
        "foo.tables.json": [("dir_a", "foo.tables.json")],
        "bar.tables.json": [("dir_a", "bar.tables.json")],
    }
    assert filter_groups_by_paper(groups, "baz") == {}


def test_has_semantic_header_value_true_when_value_matches_column():
    assert has_semantic_header_value(Row(family="family", scientific_name="Ammi majus"))


def test_has_semantic_header_value_matches_accented_value_against_normalized_column():
    assert has_semantic_header_value(Row(categoria_de_uso="categoría de uso", chorote_total="chorote total"))


def test_has_semantic_header_value_false_when_no_match():
    assert not has_semantic_header_value(
        Row(family="Apiaceae", scientific_name="Ammi majus")
    )


def test_has_semantic_header_value_false_for_numeric_columns():
    assert not has_semantic_header_value(Row(**{"0": "0", "1": "1"}))


def test_has_hints_header_value_true_when_any_value_in_hints():
    assert has_hints_header_value(
        Row(**{"0": "species", "1": "Apiaceae"}), {"species", "family"}
    )


def test_has_hints_header_value_false_when_no_value_in_hints():
    assert not has_hints_header_value(
        Row(**{"0": "Ammi majus", "1": "Apiaceae"}), {"species", "family"}
    )


def test_has_hints_header_value_ignores_semantic_columns():
    assert not has_hints_header_value(Row(family="family"), {"family"})


def test_has_hints_header_value_with_value_with_agreement():
    assert has_hints_header_value(
        Row(**{"0": [ValueWithAgreement(value="species", agreement_level=1)]}),
        {"species"},
    )


def test_is_header_row_without_hints_ignores_numeric_columns():
    assert not is_header_row(Row(**{"0": "0", "1": "1"}))


def test_is_header_row_with_hints_detects_numeric_header():
    assert is_header_row(
        Row(**{"0": "species", "1": "Apiaceae"}), hints=["species", "family"]
    )


def test_is_header_row_with_hints_false_when_no_match():
    assert not is_header_row(
        Row(**{"0": "Ammi majus", "1": "Apiaceae"}), hints=["species", "family"]
    )


def test_filter_header_rows_with_hints_removes_numeric_header_row():
    table = [
        Row(**{"0": "species", "1": "family"}),
        Row(**{"0": "Ammi majus", "1": "Apiaceae"}),
    ]
    result = merge_tablesfiles([wrap(table)])
    filtered = filter_header_rows(result, hints=["species", "family"])
    rows = filtered.tables[0].get_table_fragments()[0].rows
    assert rows == [Row(**{"0": "ammi majus", "1": "apiaceae"}, agreement_level_=1, row_=1)]


def test_filter_header_rows_without_hints_still_removes_semantic_header_rows():
    table = [
        Row(family="family", scientific_name="scientific_name"),
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
    ]
    result = merge_tablesfiles([wrap(table)])
    filtered = filter_header_rows(result)
    rows = filtered.tables[0].get_table_fragments()[0].rows
    assert rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1, row_=1)
    ]


def test_value_matches_header_returns_false_for_none():
    assert value_matches_header("family", None) == False


def test_value_matches_hints_returns_false_for_none():
    assert value_matches_hints(None, {"family", "species"}) == False


def test_to_values_with_agreement_returns_empty_list_for_none():
    assert to_values_with_agreement(None) == []


def test_table_fragment_is_empty_all_empty_rows():
    fragment = TableFragment(rows=[Row(family="", scientific_name=None)], page=1)
    assert fragment.is_empty()


def test_table_fragment_is_empty_false_when_has_data():
    fragment = TableFragment(rows=[Row(family="Apiaceae")], page=1)
    assert not fragment.is_empty()


def test_table_fragment_is_empty_true_when_no_rows():
    fragment = TableFragment(rows=[], page=1)
    assert fragment.is_empty()


def test_table_with_fragments_is_empty_all_fragments_empty():
    table = TableWithFragments(table_fragments=[
        TableFragment(rows=[Row(family="")], page=1),
        TableFragment(rows=[Row(family="")], page=2),
    ])
    assert table.is_empty()


def test_table_with_fragments_is_empty_false_when_any_fragment_has_data():
    table = TableWithFragments(table_fragments=[
        TableFragment(rows=[Row(family="")], page=1),
        TableFragment(rows=[Row(family="Apiaceae")], page=2),
    ])
    assert not table.is_empty()


def test_drop_empty_tables_removes_empty_table():
    non_empty = wrap([Row(family="Apiaceae")])
    empty = wrap([Row(family="")])
    combined = TablesFile(
        tables=non_empty.tables + empty.tables,
        citation="",
    )
    result = drop_empty_tables(combined)
    assert result.tables == non_empty.tables


def test_drop_empty_tables_removes_empty_fragments():
    non_empty_fragment = TableFragment(rows=[Row(family="Apiaceae")], page=1)
    empty_fragment = TableFragment(rows=[Row(family="")], page=2)
    table = TableWithFragments(table_fragments=[non_empty_fragment, empty_fragment])
    tablesfile = TablesFile(tables=[table], citation="")
    result = drop_empty_tables(tablesfile)
    assert result.tables == [TableWithFragments(table_fragments=[non_empty_fragment])]


def test_drop_empty_tables_keeps_all_when_none_empty():
    tablesfile = wrap([Row(family="Apiaceae"), Row(family="Fabaceae")])
    result = drop_empty_tables(tablesfile)
    assert result.tables == tablesfile.tables


def test_drop_empty_tables_returns_empty_tables_list_when_all_empty():
    tablesfile = wrap([Row(family="")])
    result = drop_empty_tables(tablesfile)
    assert result.tables == []


def test_unmatched_right_row_inserted_before_higher_row_number():
    # Verifies that unmatched right-table rows at a lower row_ position
    # are inserted before left rows at a higher row_ position, not appended at the end.
    #
    # table_1 provides 3 rows at row_=0,1,2.
    # table_2 matches the first row (row_=0, family=a, position=1).
    # table_3 contributes an unmatched row at row_=0 (j,1), inserted into the row_=0 group.
    # table_4 contributes an unmatched row at row_=0 (a,2), also in the row_=0 group.
    # table_5 contributes an unmatched row at row_=0 (x,1); must appear before row_=1 (b,1).
    table_1 = [
        Row(family="a", position="1"),
        Row(family="b", position="1"),
        Row(family="c", position="1"),
    ]
    table_2 = [Row(family="a", position="1")]
    table_3 = [Row(family="j", position="1")]
    table_4 = [Row(family="a", position="2")]
    table_5 = [Row(family="x", position="1")]

    result = merge_tablesfiles(
        [wrap(table_1), wrap(table_2), wrap(table_3), wrap(table_4), wrap(table_5)]
    )
    rows = result.tables[0].get_table_fragments()[0].rows
    assert rows == [
        Row(family="a", position="1", agreement_level_=2, row_=0),
        Row(family="j", position="1", agreement_level_=1, row_=0),
        Row(family="a", position="2", agreement_level_=1, row_=0),
        Row(family="x", position="1", agreement_level_=1, row_=0),
        Row(family="b", position="1", agreement_level_=1, row_=1),
        Row(family="c", position="1", agreement_level_=1, row_=2),
    ]
