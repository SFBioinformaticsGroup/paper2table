# pyright: reportCallIssue=false
# pyright: reportArgumentType=false
from tablemerge.tablesfile_transformer import (
    FragmentsExploder,
    NullTablesfileTransformer,
    SafeConsecutiveFragmentsCompactor,
    UnsafeConsecutiveFragmentsCompactor,
)
from tablevalidate.schema import TablesFile, TableWithFragments, TableFragment, Row


def make_tablesfile(*fragments: TableFragment, citation="") -> TablesFile:
    return TablesFile(
        tables=[TableWithFragments(table_fragments=[f]) for f in fragments],
        citation=citation,
    )


def test_null_compactor_returns_tablesfile_unchanged():
    fragment = TableFragment(
        rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
        page=2,
    )
    tablesfile = make_tablesfile(fragment)
    result = NullTablesfileTransformer().transform(tablesfile)
    assert result.tables == [TableWithFragments(table_fragments=[fragment])]


def test_safe_compactor_merges_two_consecutive_tables_with_matching_semantic_columns():
    fragment_page_2 = TableFragment(
        rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
        page=2,
    )
    fragment_page_3 = TableFragment(
        rows=[Row(scientific_name="Rattus Rattus", common_name="Rat")],
        page=3,
    )
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(table_fragments=[fragment_page_2]),
            TableWithFragments(table_fragments=[fragment_page_3]),
        ],
        citation="dont care",
    )
    result = SafeConsecutiveFragmentsCompactor().transform(tablesfile)
    assert result.tables == [
        TableWithFragments(
            table_fragments=[
                TableFragment(
                    rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
                    page=2,
                ),
                TableFragment(
                    rows=[Row(scientific_name="Rattus Rattus", common_name="Rat")],
                    page=3,
                ),
            ]
        )
    ]


def test_safe_compactor_does_not_merge_tables_with_different_semantic_columns():
    fragment_page_2 = TableFragment(
        rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
        page=2,
    )
    fragment_page_3 = TableFragment(
        rows=[Row(family="Muridae", order="Rodentia")],
        page=3,
    )
    tablesfile = make_tablesfile(fragment_page_2, fragment_page_3)
    result = SafeConsecutiveFragmentsCompactor().transform(tablesfile)
    assert result.tables == [
        TableWithFragments(table_fragments=[fragment_page_2]),
        TableWithFragments(table_fragments=[fragment_page_3]),
    ]


def test_safe_compactor_does_not_merge_tables_with_non_correlative_pages():
    fragment_page_2 = TableFragment(
        rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
        page=2,
    )
    fragment_page_4 = TableFragment(
        rows=[Row(scientific_name="Rattus Rattus", common_name="Rat")],
        page=4,
    )
    tablesfile = make_tablesfile(fragment_page_2, fragment_page_4)
    result = SafeConsecutiveFragmentsCompactor().transform(tablesfile)
    assert result.tables == [
        TableWithFragments(table_fragments=[fragment_page_2]),
        TableWithFragments(table_fragments=[fragment_page_4]),
    ]


def test_safe_compactor_does_not_merge_tables_with_numeric_columns():
    fragment_page_2 = TableFragment(
        rows=[Row(**{"0": "Mus Musculus", "1": "Mouse"})],
        page=2,
    )
    fragment_page_3 = TableFragment(
        rows=[Row(**{"0": "Rattus Rattus", "1": "Rat"})],
        page=3,
    )
    tablesfile = make_tablesfile(fragment_page_2, fragment_page_3)
    result = SafeConsecutiveFragmentsCompactor().transform(tablesfile)
    assert result.tables == [
        TableWithFragments(table_fragments=[fragment_page_2]),
        TableWithFragments(table_fragments=[fragment_page_3]),
    ]


def test_unsafe_compactor_merges_tables_with_numeric_columns_of_same_count():
    fragment_page_2 = TableFragment(
        rows=[Row(**{"0": "Mus Musculus", "1": "Mouse"})],
        page=2,
    )
    fragment_page_3 = TableFragment(
        rows=[Row(**{"0": "Rattus Rattus", "1": "Rat"})],
        page=3,
    )
    tablesfile = make_tablesfile(fragment_page_2, fragment_page_3)
    result = UnsafeConsecutiveFragmentsCompactor().transform(tablesfile)
    assert result.tables == [
        TableWithFragments(
            table_fragments=[
                TableFragment(
                    rows=[Row(**{"0": "Mus Musculus", "1": "Mouse"})],
                    page=2,
                ),
                TableFragment(
                    rows=[Row(**{"0": "Rattus Rattus", "1": "Rat"})],
                    page=3,
                ),
            ]
        )
    ]


def test_unsafe_compactor_does_not_merge_tables_with_numeric_columns_of_different_count():
    fragment_page_2 = TableFragment(
        rows=[Row(**{"0": "Mus Musculus", "1": "Mouse"})],
        page=2,
    )
    fragment_page_3 = TableFragment(
        rows=[Row(**{"0": "Rattus Rattus", "1": "Rat", "2": "Rodentia"})],
        page=3,
    )
    tablesfile = make_tablesfile(fragment_page_2, fragment_page_3)
    result = UnsafeConsecutiveFragmentsCompactor().transform(tablesfile)
    assert result.tables == [
        TableWithFragments(table_fragments=[fragment_page_2]),
        TableWithFragments(table_fragments=[fragment_page_3]),
    ]


def test_safe_compactor_merges_three_consecutive_matching_tables_into_one():
    fragment_page_2 = TableFragment(
        rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
        page=2,
    )
    fragment_page_3 = TableFragment(
        rows=[Row(scientific_name="Rattus Rattus", common_name="Rat")],
        page=3,
    )
    fragment_page_4 = TableFragment(
        rows=[Row(scientific_name="Canis Lupus", common_name="Wolf")],
        page=4,
    )
    tablesfile = make_tablesfile(fragment_page_2, fragment_page_3, fragment_page_4)
    result = SafeConsecutiveFragmentsCompactor().transform(tablesfile)
    assert result.tables == [
        TableWithFragments(
            table_fragments=[
                TableFragment(
                    rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
                    page=2,
                ),
                TableFragment(
                    rows=[Row(scientific_name="Rattus Rattus", common_name="Rat")],
                    page=3,
                ),
                TableFragment(
                    rows=[Row(scientific_name="Canis Lupus", common_name="Wolf")],
                    page=4,
                ),
            ]
        )
    ]


def test_safe_compactor_merges_matching_pair_and_keeps_non_matching_table_separate():
    fragment_page_2 = TableFragment(
        rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
        page=2,
    )
    fragment_page_3 = TableFragment(
        rows=[Row(scientific_name="Rattus Rattus", common_name="Rat")],
        page=3,
    )
    fragment_page_4 = TableFragment(
        rows=[Row(family="Muridae", order="Rodentia")],
        page=4,
    )
    tablesfile = make_tablesfile(fragment_page_2, fragment_page_3, fragment_page_4)
    result = SafeConsecutiveFragmentsCompactor().transform(tablesfile)
    assert result.tables == [
        TableWithFragments(
            table_fragments=[
                TableFragment(
                    rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
                    page=2,
                ),
                TableFragment(
                    rows=[Row(scientific_name="Rattus Rattus", common_name="Rat")],
                    page=3,
                ),
            ]
        ),
        TableWithFragments(table_fragments=[fragment_page_4]),
    ]


def test_safe_compactor_does_not_crash_on_empty_fragment_list():
    fragment_page_2 = TableFragment(
        rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
        page=2,
    )
    fragment_page_3 = TableFragment(
        rows=[Row(scientific_name="Rattus Rattus", common_name="Rat")],
        page=3,
    )
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(table_fragments=[]),
            TableWithFragments(table_fragments=[fragment_page_2]),
            TableWithFragments(table_fragments=[fragment_page_3]),
        ],
        citation="",
    )
    result = SafeConsecutiveFragmentsCompactor().transform(tablesfile)
    assert result.tables == [
        TableWithFragments(table_fragments=[]),
        TableWithFragments(
            table_fragments=[
                TableFragment(
                    rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
                    page=2,
                ),
                TableFragment(
                    rows=[Row(scientific_name="Rattus Rattus", common_name="Rat")],
                    page=3,
                ),
            ]
        ),
    ]


def test_safe_compactor_merges_tables_around_empty_row_table():
    fragment_page_2 = TableFragment(
        rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
        page=2,
    )
    empty_fragment_page_3 = TableFragment(rows=[], page=3)
    fragment_page_4 = TableFragment(
        rows=[Row(scientific_name="Rattus Rattus", common_name="Rat")],
        page=4,
    )
    tablesfile = make_tablesfile(
        fragment_page_2, empty_fragment_page_3, fragment_page_4
    )
    result = SafeConsecutiveFragmentsCompactor().transform(tablesfile)
    assert result.tables == [
        TableWithFragments(
            table_fragments=[
                TableFragment(
                    rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
                    page=2,
                ),
                TableFragment(rows=[], page=3),
                TableFragment(
                    rows=[Row(scientific_name="Rattus Rattus", common_name="Rat")],
                    page=4,
                ),
            ]
        )
    ]


def test_safe_compactor_merges_two_tables_on_the_same_page_with_matching_columns():
    fragment_a = TableFragment(
        rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
        page=2,
    )
    fragment_b = TableFragment(
        rows=[Row(scientific_name="Rattus Rattus", common_name="Rat")],
        page=2,
    )
    tablesfile = make_tablesfile(fragment_a, fragment_b)
    result = SafeConsecutiveFragmentsCompactor().transform(tablesfile)
    assert result.tables == [
        TableWithFragments(
            table_fragments=[
                TableFragment(
                    rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
                    page=2,
                ),
                TableFragment(
                    rows=[Row(scientific_name="Rattus Rattus", common_name="Rat")],
                    page=2,
                ),
            ]
        )
    ]


def test_safe_compactor_does_not_merge_two_tables_on_the_same_page_with_different_columns():
    fragment_a = TableFragment(
        rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
        page=2,
    )
    fragment_b = TableFragment(
        rows=[Row(family="Muridae", order="Rodentia")],
        page=2,
    )
    tablesfile = make_tablesfile(fragment_a, fragment_b)
    result = SafeConsecutiveFragmentsCompactor().transform(tablesfile)
    assert result.tables == [
        TableWithFragments(table_fragments=[fragment_a]),
        TableWithFragments(table_fragments=[fragment_b]),
    ]


def test_unsafe_compactor_merges_semantic_tables_on_non_consecutive_pages():
    fragment_page_2 = TableFragment(
        rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
        page=2,
    )
    fragment_page_5 = TableFragment(
        rows=[Row(scientific_name="Rattus Rattus", common_name="Rat")],
        page=5,
    )
    tablesfile = make_tablesfile(fragment_page_2, fragment_page_5)
    result = UnsafeConsecutiveFragmentsCompactor().transform(tablesfile)
    assert result.tables == [
        TableWithFragments(
            table_fragments=[
                TableFragment(
                    rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
                    page=2,
                ),
                TableFragment(
                    rows=[Row(scientific_name="Rattus Rattus", common_name="Rat")],
                    page=5,
                ),
            ]
        )
    ]


def test_safe_compactor_does_not_merge_semantic_tables_on_non_consecutive_pages():
    fragment_page_2 = TableFragment(
        rows=[Row(scientific_name="Mus Musculus", common_name="Mouse")],
        page=2,
    )
    fragment_page_5 = TableFragment(
        rows=[Row(scientific_name="Rattus Rattus", common_name="Rat")],
        page=5,
    )
    tablesfile = make_tablesfile(fragment_page_2, fragment_page_5)
    result = SafeConsecutiveFragmentsCompactor().transform(tablesfile)
    assert result.tables == [
        TableWithFragments(table_fragments=[fragment_page_2]),
        TableWithFragments(table_fragments=[fragment_page_5]),
    ]


def test_exploder_with_single_table():
    row_a = Row(family="Apiaceae", scientific_name="Ammi majus L.")
    row_b = Row(family="Rosaceae", scientific_name="Rosa canina L.")

    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(rows=[row_a], page=1),
                    TableFragment(rows=[row_b], page=2),
                ]
            )
        ],
        citation="",
        uuid="uuid-1",
    )

    result = FragmentsExploder().transform(tablesfile)

    assert len(result.tables) == 2
    assert len(result.tables[0].get_table_fragments()) == 1
    assert len(result.tables[1].get_table_fragments()) == 1


def test_exploder_with_multiple_tables():

    row_a = Row(family="Apiaceae", scientific_name="Ammi majus L.")
    row_b = Row(family="Rosaceae", scientific_name="Rosa canina L.")

    tablesfile = TablesFile(
        tables=[
            TableWithFragments(table_fragments=[TableFragment(rows=[row_a], page=1)]),
            TableWithFragments(table_fragments=[TableFragment(rows=[row_b], page=2)]),
        ],
        citation="",
        uuid="uuid-2",
    )

    result = FragmentsExploder().transform(tablesfile)

    assert len(result.tables) == 2
    assert len(result.tables[0].get_table_fragments()) == 1
    assert len(result.tables[1].get_table_fragments()) == 1
