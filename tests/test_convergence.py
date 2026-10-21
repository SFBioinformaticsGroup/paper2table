# pyright: reportCallIssue=false
from tablevalidate.schema import (
    Row,
    TableFragment,
    TableWithFragments,
    TablesFile,
    ValueWithAgreement,
)


def test_table_fragment_get_convergent_rows_all_unique():
    fragment = TableFragment(
        rows=[
            Row(species="Ammi majus", row_=1, sources_=["uuid1"]),
            Row(species="Carum carvi", row_=2, sources_=["uuid1"]),
        ],
        page=1,
    )
    assert fragment.get_convergent_rows() == [
        Row(species="Ammi majus", row_=1, sources_=["uuid1"]),
        Row(species="Carum carvi", row_=2, sources_=["uuid1"]),
    ]


def test_table_fragment_get_convergent_rows_multivalued_excluded():
    fragment = TableFragment(
        rows=[
            Row(
                species=[
                    ValueWithAgreement(value="Ammi majus", agreement_level=1),
                    ValueWithAgreement(value="Carum carvi", agreement_level=1),
                ],
                row_=1,
            )
        ],
        page=1,
    )
    assert fragment.get_convergent_rows() == []


def test_table_fragment_get_convergent_rows_multivalued_excluded_single_valued_kept():
    fragment = TableFragment(
        rows=[
            Row(
                species=[
                    ValueWithAgreement(value="Ammi majus", agreement_level=1),
                    ValueWithAgreement(value="Ammi visnaga", agreement_level=1),
                ],
                row_=1,
                agreement_level_=2,
                sources_=["uuid1", "uuid2"],
            ),
            Row(species="Carum carvi", row_=2, agreement_level_=2, sources_=["uuid1", "uuid2"]),
        ],
        page=1,
    )
    assert fragment.get_convergent_rows(level=3) == [
        Row(species="Carum carvi", row_=2, agreement_level_=2, sources_=["uuid1", "uuid2"])
    ]


def test_table_get_convergent_fragments_includes_fully_convergent_fragment():
    convergent_fragment = TableFragment(
        rows=[Row(species="Ammi majus", row_=1, agreement_level_=2, sources_=["uuid1", "uuid2"])],
        page=1,
    )
    non_convergent_fragment = TableFragment(
        rows=[
            Row(
                species=[
                    ValueWithAgreement(value="Carum carvi", agreement_level=1),
                    ValueWithAgreement(value="Zea mays", agreement_level=1),
                ],
                row_=1,
                agreement_level_=2,
                sources_=["uuid1", "uuid2"],
            )
        ],
        page=2,
    )
    table = TableWithFragments(
        table_fragments=[convergent_fragment, non_convergent_fragment]
    )
    assert table.get_convergent_fragments(level=3) == [convergent_fragment]


def test_table_get_convergent_fragments_empty_when_none_convergent():
    fragment = TableFragment(
        rows=[
            Row(
                species=[
                    ValueWithAgreement(value="Ammi majus", agreement_level=1),
                    ValueWithAgreement(value="Carum carvi", agreement_level=1),
                ],
                row_=1,
            )
        ],
        page=1,
    )
    table = TableWithFragments(table_fragments=[fragment])
    assert table.get_convergent_fragments() == []


def test_tablesfile_get_convergent_tables_includes_fully_convergent_table():
    convergent_table = TableWithFragments(
        table_fragments=[
            TableFragment(
                rows=[Row(species="Ammi majus", row_=1, agreement_level_=2, sources_=["uuid1", "uuid2"])],
                page=1,
            )
        ]
    )
    non_convergent_table = TableWithFragments(
        table_fragments=[
            TableFragment(
                rows=[
                    Row(
                        species=[
                            ValueWithAgreement(value="Carum carvi", agreement_level=1),
                            ValueWithAgreement(value="Zea mays", agreement_level=1),
                        ],
                        row_=1,
                        agreement_level_=2,
                        sources_=["uuid1", "uuid2"],
                    )
                ],
                page=2,
            )
        ]
    )
    tablesfile = TablesFile(
        tables=[convergent_table, non_convergent_table], citation="Mamani 2020"
    )
    assert tablesfile.get_convergent_tables(level=3) == [convergent_table]


def test_tablesfile_get_convergent_tables_empty_when_none_convergent():
    table = TableWithFragments(
        table_fragments=[
            TableFragment(
                rows=[
                    Row(
                        species=[
                            ValueWithAgreement(value="Ammi majus", agreement_level=1),
                            ValueWithAgreement(value="Ammi", agreement_level=1),
                        ],
                        row_=1,
                    ),
                    Row(species="Carum carvi", row_=1),
                ],
                page=1,
            )
        ]
    )
    tablesfile = TablesFile(tables=[table], citation="Mamani 2020")
    assert tablesfile.get_convergent_tables() == []
