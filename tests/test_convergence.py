from tablevalidate.schema import Row, TableFragment, TableWithFragments, TablesFile


def test_table_fragment_get_convergent_rows_all_unique():
    fragment = TableFragment(
        rows=[Row(species="Ammi majus", row_=1), Row(species="Carum carvi", row_=2)],
        page=1,
    )
    assert fragment.get_convergent_rows() == [
        Row(species="Ammi majus", row_=1),
        Row(species="Carum carvi", row_=2),
    ]


def test_table_fragment_get_convergent_rows_duplicate_excluded():
    fragment = TableFragment(
        rows=[Row(species="Ammi majus", row_=1), Row(species="Carum carvi", row_=1)],
        page=1,
    )
    assert fragment.get_convergent_rows() == []


def test_table_fragment_get_convergent_rows_none_row_id_excluded():
    fragment = TableFragment(
        rows=[Row(species="Ammi majus"), Row(species="Carum carvi", row_=1)], page=1
    )
    assert fragment.get_convergent_rows() == [Row(species="Carum carvi", row_=1)]


def test_table_fragment_get_row_groups_groups_by_row_id():
    fragment = TableFragment(
        rows=[Row(species="Ammi majus"), Row(species="Carum carvi", row_=1), Row(species="Zea mays", row_=1)],
        page=1,
    )
    assert fragment.get_row_groups() == {1: [Row(species="Carum carvi", row_=1), Row(species="Zea mays", row_=1)]}


def test_table_fragment_get_row_groups_empty_when_no_row_id():
    fragment = TableFragment(rows=[Row(species="Ammi majus"), Row(species="Carum carvi")], page=1)
    assert fragment.get_row_groups() == {}


def test_table_get_convergent_fragments_includes_fully_convergent_fragment():
    convergent_fragment = TableFragment(rows=[Row(species="Ammi majus", row_=1)], page=1)
    non_convergent_fragment = TableFragment(
        rows=[Row(species="Carum carvi", row_=1), Row(species="Zea mays", row_=1)], page=2
    )
    table = TableWithFragments(table_fragments=[convergent_fragment, non_convergent_fragment])
    assert table.get_convergent_fragments() == [convergent_fragment]


def test_table_get_convergent_fragments_empty_when_none_convergent():
    fragment = TableFragment(
        rows=[Row(species="Ammi majus", row_=1), Row(species="Carum carvi", row_=1)], page=1
    )
    table = TableWithFragments(table_fragments=[fragment])
    assert table.get_convergent_fragments() == []


def test_tablesfile_get_convergent_tables_includes_fully_convergent_table():
    convergent_table = TableWithFragments(
        table_fragments=[TableFragment(rows=[Row(species="Ammi majus", row_=1)], page=1)]
    )
    non_convergent_table = TableWithFragments(
        table_fragments=[
            TableFragment(
                rows=[Row(species="Carum carvi", row_=1), Row(species="Zea mays", row_=1)], page=2
            )
        ]
    )
    tablesfile = TablesFile(tables=[convergent_table, non_convergent_table], citation="Mamani 2020")
    assert tablesfile.get_convergent_tables() == [convergent_table]


def test_tablesfile_get_convergent_tables_empty_when_none_convergent():
    table = TableWithFragments(
        table_fragments=[
            TableFragment(
                rows=[Row(species="Ammi majus", row_=1), Row(species="Carum carvi", row_=1)], page=1
            )
        ]
    )
    tablesfile = TablesFile(tables=[table], citation="Mamani 2020")
    assert tablesfile.get_convergent_tables() == []
