# pyright: reportCallIssue=false

from table2csv.__main__ import build_dataframes
from tablevalidate.schema import Row, TableFragment, TableWithFragments, TablesFile, ValueWithAgreement


def test_build_dataframes_includes_page_column():
    tablesfile = TablesFile(
        citation="Mamani 2020",
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(rows=[Row(species="Ammi majus")], page=3)
                ]
            )
        ],
    )
    dataframes = build_dataframes({"mamani_2020.tables.json": tablesfile})
    rows = dataframes["mamani_2020.tables.json"][0].to_dict(orient="records")
    assert rows == [{"$page": 3, "species": "Ammi majus"}]


def test_build_dataframes_page_column_reflects_fragment_page():
    tablesfile = TablesFile(
        citation="Mamani 2020",
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(rows=[Row(species="Ammi majus")], page=2),
                    TableFragment(rows=[Row(species="Carum carvi")], page=5),
                ]
            )
        ],
    )
    dataframes = build_dataframes({"mamani_2020.tables.json": tablesfile})
    rows = dataframes["mamani_2020.tables.json"][0].to_dict(orient="records")
    assert rows == [
        {"$page": 2, "species": "Ammi majus"},
        {"$page": 5, "species": "Carum carvi"},
    ]


def test_build_dataframes_serializes_value_with_agreement_as_newline_separated():
    tablesfile = TablesFile(
        citation="Mamani 2020",
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(
                        rows=[
                            Row(
                                species=[
                                    ValueWithAgreement(value="Ammi majus", agreement_level=2),
                                    ValueWithAgreement(value="Ammi visnaga", agreement_level=1),
                                ]
                            )
                        ],
                        page=1,
                    )
                ]
            )
        ],
    )
    dataframes = build_dataframes({"mamani_2020.tables.json": tablesfile})
    rows = dataframes["mamani_2020.tables.json"][0].to_dict(orient="records")
    assert rows == [{"$page": 1, "species": "Ammi majus\nAmmi visnaga"}]
