from table2csv.__main__ import build_dataframes
from tablevalidate.schema import Row, TableFragment, TableWithFragments, TablesFile


def test_build_dataframes_includes_page_column():
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(rows=[Row(species="Ammi majus")], page=3)
                ]
            )
        ]
    )
    dataframes = build_dataframes({"mamani_2020.tables.json": tablesfile})
    rows = dataframes["mamani_2020.tables.json"][0].to_dict(orient="records")
    assert rows == [{"$page": 3, "species": "Ammi majus"}]


def test_build_dataframes_page_column_reflects_fragment_page():
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(rows=[Row(species="Ammi majus")], page=2),
                    TableFragment(rows=[Row(species="Carum carvi")], page=5),
                ]
            )
        ]
    )
    dataframes = build_dataframes({"mamani_2020.tables.json": tablesfile})
    rows = dataframes["mamani_2020.tables.json"][0].to_dict(orient="records")
    assert rows == [
        {"$page": 2, "species": "Ammi majus"},
        {"$page": 5, "species": "Carum carvi"},
    ]
