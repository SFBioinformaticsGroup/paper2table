# pyright: reportCallIssue=false
import pytest
from tablemerge.merge import (
    merge_tablesfiles,
    merge_rows,
    SimpleCountAgreement,
    DistinctReadersAgreement,
    filter_semantic_columns,
)
from tablemerge.columns_aligner import find_column_mapping
from utils.rows import is_empty_row
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
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1)
    ]


def test_single_table_with_row_agreement():
    table = [Row(family=" Apiaceae ", scientific_name="Ammi majus L.")]

    result = merge_tablesfiles([wrap(table)], agreement=SimpleCountAgreement())
    assert len(result.tables) == 1
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1)
    ]


def test_two_identical_tables():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]

    result = merge_tablesfiles([wrap(table), wrap(table)])
    assert len(result.tables) == 1
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2)
    ]


def test_two_identical_tables_with_row_agreement():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]

    result = merge_tablesfiles(
        [wrap(table), wrap(table)], agreement=SimpleCountAgreement()
    )
    assert len(result.tables) == 1
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2)
    ]


def test_two_tables_with_non_normalized_columns():
    table_1 = [Row(family=" Apiaceae ", scientific_name=" Ammi majus L. ")]
    table_2 = [Row(family="apiaceae", scientific_name="ammi majus l.")]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2)
    ]


def test_two_tables_with_different_column_names():
    table_1 = [Row(family=" Apiaceae ", scientific_name=" Ammi majus L. ")]
    table_2 = [Row(**{"0": "apiaceae", "1": "ammi majus l."})]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2),
    ]


def test_two_tables_with_different_column_names_and_row_agreement():
    table_1 = [Row(family=" Apiaceae ", scientific_name=" Ammi majus L. ")]
    table_2 = [Row(**{"0": "apiaceae", "1": "ammi majus l."})]

    result = merge_tablesfiles(
        [wrap(table_1), wrap(table_2)], agreement=SimpleCountAgreement()
    )
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2),
    ]


def test_two_tables_with_different_values():
    table_1 = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    table_2 = [
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
    ]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=1),
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
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1),
    ]

    assert result.tables[0].table_fragments[1].page == 2
    assert result.tables[0].table_fragments[1].rows == [
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=1),
    ]


def test_two_tables_with_mixed_values():
    table_1 = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    table_2 = [
        Row(family="Apiaceae", scientific_name="Ammi majus L."),
        Row(family="Rosaceae", scientific_name="Rosa canina L."),
    ]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=1),
    ]


def test_three_tables_with_different_values():
    table_1 = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    table_2 = [Row(family="Rosaceae", scientific_name="Rosa canina L.")]
    table_3 = [Row(family="Lamiaceae", scientific_name="Mentha spicata L.")]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2), wrap(table_3)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=1),
        Row(
            family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1
        ),
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
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=2),
        Row(
            family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1
        ),
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
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2),
        Row(family="apiaceae", scientific_name="ammi", agreement_level_=1),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=2),
        Row(
            family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1
        ),
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
        Row(family="apiaceae", scientific_name="ammi", agreement_level_=1),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=1),
        Row(
            family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1
        ),
        # TODO add it not at bottom but next to the closest one
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1),
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
        Row(family="apiaceae", scientific_name="ammi", agreement_level_=1),
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=1),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=2),
        Row(
            family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1
        ),
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
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2),
        Row(family="apiaceae", scientific_name="ammi", agreement_level_=1),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=2),
        Row(
            family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1
        ),
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
    rows = result.tables[0].table_fragments[0].rows
    assert rows[0].sources_ == ["uuid-a"]


def test_sources_merged_on_matched_rows():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    result = merge_tablesfiles([wrap(table, uuid="uuid-a"), wrap(table, uuid="uuid-b")])
    rows = result.tables[0].table_fragments[0].rows
    assert rows[0].sources_ == ["uuid-a", "uuid-b"]


def test_sources_only_left_uuid_on_unmatched_left_row():
    table_1 = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    table_2 = [Row(family="Rosaceae", scientific_name="Rosa canina L.")]
    result = merge_tablesfiles(
        [wrap(table_1, uuid="uuid-a"), wrap(table_2, uuid="uuid-b")]
    )
    rows = result.tables[0].table_fragments[0].rows
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
    rows = result.tables[0].table_fragments[0].rows
    # "Rosaceae" was skipped (appears before the match in right table)
    rosaceae_row = next(r for r in rows if r.get_columns().get("family") == "rosaceae")
    assert rosaceae_row.sources_ == ["uuid-b"]
    # "Apiaceae" was matched
    apiaceae_row = next(r for r in rows if r.get_columns().get("family") == "apiaceae")
    assert apiaceae_row.sources_ == ["uuid-a", "uuid-b"]


def test_two_tables_with_unicode_variant_values():
    # look the same but are different ñ
    table_1 = [Row(common_name="pezuña de vaca")]
    table_2 = [Row(common_name="pezuña de vaca")]

    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(common_name="pezuña de vaca", agreement_level_=2)
    ]


def test_sources_deduped_when_same_uuid_appears_twice():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    result = merge_tablesfiles([wrap(table, uuid="uuid-a"), wrap(table, uuid="uuid-a")])
    rows = result.tables[0].table_fragments[0].rows
    assert rows[0].sources_ == ["uuid-a"]


def test_sources_none_when_no_uuid_on_tablesfiles():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    result = merge_tablesfiles([wrap(table), wrap(table)])
    rows = result.tables[0].table_fragments[0].rows
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
    assert is_empty_row(Row(family="", scientific_name=""))


def test_is_empty_row_whitespace_only():
    assert is_empty_row(Row(family="  ", scientific_name="\t"))


def test_is_empty_row_none_values():
    assert is_empty_row(Row(family=None, scientific_name=None))


def test_is_empty_row_metadata_fields_ignored():
    assert is_empty_row(Row(family="", agreement_level_=2, sources_=["abc"]))


def test_is_empty_row_not_empty_when_has_data():
    assert not is_empty_row(Row(family="Apiaceae", scientific_name=""))


def test_is_empty_row_value_with_agreement_all_empty():
    assert is_empty_row(Row(family=[ValueWithAgreement(value="", agreement_level=1)]))


def test_is_empty_row_value_with_agreement_has_data():
    assert not is_empty_row(
        Row(family=[ValueWithAgreement(value="Apiaceae", agreement_level=1)])
    )


def test_merge_filters_empty_rows_from_single_table():
    table = [
        Row(family="Apiaceae", scientific_name=""),
        Row(family="", scientific_name=""),
    ]
    result = merge_tablesfiles([wrap(table)])
    rows = result.tables[0].table_fragments[0].rows
    assert len(rows) == 1
    assert rows[0].family == "apiaceae"


def test_merge_filters_whitespace_only_rows():
    table = [
        Row(family="  ", scientific_name="\n"),
        Row(family="Rosaceae", scientific_name="Rosa"),
    ]
    result = merge_tablesfiles([wrap(table)])
    rows = result.tables[0].table_fragments[0].rows
    assert len(rows) == 1
    assert rows[0].family == "rosaceae"


def test_merge_filters_empty_rows_from_two_tables():
    table_1 = [Row(family="Apiaceae"), Row(family="")]
    table_2 = [Row(family="Apiaceae"), Row(family="")]
    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    rows = result.tables[0].table_fragments[0].rows
    assert len(rows) == 1
    assert rows[0].family == "apiaceae"


def test_merge_keeps_rows_with_partial_data():
    table = [
        Row(family="Apiaceae", scientific_name=""),
        Row(family="", scientific_name=""),
    ]
    result = merge_tablesfiles([wrap(table)])
    rows = result.tables[0].table_fragments[0].rows
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
    rows = filtered.tables[0].table_fragments[0].rows
    assert len(rows) == 1
    assert rows[0].get_columns() == {"family": "apiaceae"}


def test_filter_semantic_columns_keeps_all_if_no_numeric():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus")]
    result = merge_tablesfiles([wrap(table)])
    filtered = filter_semantic_columns(result)
    rows = filtered.tables[0].table_fragments[0].rows
    assert len(rows) == 1
    assert set(rows[0].get_columns().keys()) == {"family", "scientific_name"}



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
    assert result.tables[0].table_fragments[0].rows == [
        Row(
            family="apiaceae",
            scientific_name="ammi majus l.",
            agreement_level_=2,
            sources_=["uuid-1", "uuid-2"],
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
    assert result.tables[0].table_fragments[0].rows == [
        Row(
            family="apiaceae",
            scientific_name="ammi majus l.",
            agreement_level_=1,
            sources_=["uuid-1", "uuid-2"],
        )
    ]


def test_merge_two_tables_agent_and_non_agent_reader():
    table = [Row(family="Apiaceae", scientific_name="Ammi majus L.")]
    agreement = DistinctReadersAgreement({"uuid-1": "pdfplumber", "uuid-2": "gemini"})
    result = merge_tablesfiles(
        [wrap(table, uuid="uuid-1"), wrap(table, uuid="uuid-2")],
        agreement=agreement,
    )
    assert result.tables[0].table_fragments[0].rows == [
        Row(
            family="apiaceae",
            scientific_name="ammi majus l.",
            agreement_level_=2,
            sources_=["uuid-1", "uuid-2"],
        )
    ]

def make_fragment(rows: list[Row]) -> TableFragment:
    return TableFragment(rows=rows, page=1)


def test_find_column_mapping_right_numeric_to_left_semantic():
    # "0" vs "family": {"apiaceae","rosaceae"} ∩ {"apiaceae","rosaceae"} = 2/2 = 1.0
    # "1" vs "scientific_name": same → 1.0
    left = make_fragment([
        Row(**{"family": "Apiaceae", "scientific_name": "Ammi majus L."}),
        Row(**{"family": "Rosaceae", "scientific_name": "Rosa canina L."}),
    ])
    right = make_fragment([
        Row(**{"0": "Apiaceae", "1": "Ammi majus L."}),
        Row(**{"0": "Rosaceae", "1": "Rosa canina L."}),
    ])
    assert find_column_mapping(left, right) == {"0": "family", "1": "scientific_name"}


def test_find_column_mapping_left_numeric_to_right_semantic():
    # Symmetric direction: left is numeric, right is semantic
    left = make_fragment([
        Row(**{"0": "lunes", "1": "monday"}),
        Row(**{"0": "martes", "1": "tuesday"}),
    ])
    right = make_fragment([
        Row(**{"dia": "lunes", "day": "monday"}),
        Row(**{"dia": "martes", "day": "tuesday"}),
    ])
    assert find_column_mapping(left, right) == {"0": "dia", "1": "day"}


def test_find_column_mapping_both_semantic_returns_empty():
    left = make_fragment([Row(**{"family": "Apiaceae"})])
    right = make_fragment([Row(**{"family": "Apiaceae"})])
    assert find_column_mapping(left, right) == {}


def test_find_column_mapping_both_numeric_returns_empty():
    left = make_fragment([Row(**{"0": "Apiaceae"})])
    right = make_fragment([Row(**{"0": "Apiaceae"})])
    assert find_column_mapping(left, right) == {}


def test_find_column_mapping_no_value_overlap_returns_empty():
    # "0" vs "family": {"red","blue"} ∩ {"apiaceae","rosaceae"} = 0/4 = 0.0
    # 0.0 < 0.5 (default threshold) → no mapping
    left = make_fragment([
        Row(**{"family": "Apiaceae"}),
        Row(**{"family": "Rosaceae"}),
    ])
    right = make_fragment([
        Row(**{"0": "red"}),
        Row(**{"0": "blue"}),
    ])
    assert find_column_mapping(left, right) == {}


def test_find_column_mapping_partial_overlap_above_threshold():
    # "0" vs "family": {"apiaceae"} ∩ {"apiaceae","rosaceae"} = 1/2 = 0.5
    # 0.5 >= 0.5 (default threshold) → matches
    left = make_fragment([
        Row(**{"family": "Apiaceae"}),
        Row(**{"family": "Rosaceae"}),
    ])
    right = make_fragment([
        Row(**{"0": "Apiaceae"}),
    ])
    assert find_column_mapping(left, right) == {"0": "family"}


@pytest.mark.parametrize("threshold,expected", [
    # Jaccard("0" vs "family") = |{"apiaceae"}| / |{"apiaceae","rosaceae","lamiaceae"}| = 1/3 ≈ 0.33
    (1.0,  {}),               # 0.33 < 1.0 → no match
    (0.5,  {}),               # 0.33 < 0.5 → no match
    (0.34, {}),               # 0.33 < 0.34 → no match
    (0.33, {"0": "family"}),  # 0.33 >= 0.33 → match
    (0.3,  {"0": "family"}),  # 0.33 >= 0.3 → match
    (0.0,  {"0": "family"}),  # 0.33 >= 0.0 → match
])
def test_find_column_mapping_threshold_controls_match(threshold, expected):
    # left "family" has 3 values; right "0" shares only 1 of them → Jaccard = 1/3
    left = make_fragment([
        Row(**{"family": "Apiaceae"}),
        Row(**{"family": "Rosaceae"}),
        Row(**{"family": "Lamiaceae"}),
    ])
    right = make_fragment([Row(**{"0": "Apiaceae"})])
    assert find_column_mapping(left, right, threshold=threshold) == expected


@pytest.mark.parametrize("threshold,expected", [
    # Jaccard("0" vs "family") = |{"apiaceae"}| / |{"apiaceae","rosaceae"}| = 1/2 = 0.5
    (0.6,  {}),               # 0.5 < 0.6 → no match
    (0.5,  {"0": "family"}),  # 0.5 >= 0.5 → match (at boundary)
    (0.4,  {"0": "family"}),  # 0.5 >= 0.4 → match
])
def test_find_column_mapping_threshold_boundary(threshold, expected):
    # left "family" has 2 values; right "0" shares exactly 1 → Jaccard = 0.5
    left = make_fragment([
        Row(**{"family": "Apiaceae"}),
        Row(**{"family": "Rosaceae"}),
    ])
    right = make_fragment([Row(**{"0": "Apiaceae"})])
    assert find_column_mapping(left, right, threshold=threshold) == expected


def test_find_column_mapping_empty_fragment():
    left = make_fragment([])
    right = make_fragment([Row(**{"0": "Apiaceae"})])
    assert find_column_mapping(left, right) == {}


def test_find_column_mapping_one_col_matches_one_does_not():
    # "0" vs "family": {"apiaceae","rosaceae"} → 1.0 → matches
    # "1" vs "scientific_name": {"zzz","www"} ∩ {"ammi majus l.","rosa canina l."} = 0/4 = 0.0 → no match
    left = make_fragment([
        Row(**{"family": "Apiaceae", "scientific_name": "Ammi majus L."}),
        Row(**{"family": "Rosaceae", "scientific_name": "Rosa canina L."}),
    ])
    right = make_fragment([
        Row(**{"0": "Apiaceae", "1": "zzz"}),
        Row(**{"0": "Rosaceae", "1": "www"}),
    ])
    assert find_column_mapping(left, right) == {"0": "family"}



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
    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=2),
        Row(family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1),
        Row(family="betulaceae", scientific_name="betula pendula l.", agreement_level_=1),
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
        [wrap(table_1), wrap(table_2)], agreement=SimpleCountAgreement()
    )
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=2),
        Row(family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1),
        Row(family="betulaceae", scientific_name="betula pendula l.", agreement_level_=1),
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
    result = merge_tablesfiles([wrap(table_1), wrap(table_2)])
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=2),
        Row(family="betulaceae", scientific_name="betula pendula l.", agreement_level_=1),
        Row(family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1),
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
    assert result.tables[0].table_fragments[0].rows == [
        Row(family="apiaceae", scientific_name="ammi majus l.", agreement_level_=2),
        Row(family="rosaceae", scientific_name="rosa canina l.", agreement_level_=1),
        Row(family="lamiaceae", scientific_name="mentha spicata l.", agreement_level_=1),
    ]
