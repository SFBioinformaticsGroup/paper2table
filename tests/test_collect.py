import json
from pathlib import Path

from tablegather.collect import gather_tablesfiles
from tablegather.__main__ import compute_sources, write_gather_metadata
from tablevalidate.schema import (
    TablesFile,
    TableFragment,
    TableWithFragments,
    Row,
)


def wrap(rows: list[Row], citation: str = "", page: int = 1) -> tuple[TablesFile, Path]:
    tablesfile = TablesFile(
        tables=[TableWithFragments(table_fragments=[TableFragment(rows=rows, page=page)])],
        citation=citation,
    )
    return tablesfile, Path(f"{citation or 'unnamed'}.tables.json")


def test_single_file_adds_citation_column():
    tablesfile, path = wrap([Row(species="Ammi majus")], citation="Mamani 2020")
    result = gather_tablesfiles([(tablesfile, path)], citation_column="citation", key_columns=[])
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [Row(citation="Mamani 2020", species="Ammi majus")]


def test_two_files_distinct_citations_combined():
    file_a, path_a = wrap([Row(species="Ammi majus")], citation="Mamani 2020")
    file_b, path_b = wrap([Row(species="Carum carvi")], citation="Jones 2021")
    result = gather_tablesfiles(
        [(file_a, path_a), (file_b, path_b)], citation_column="citation", key_columns=[]
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(citation="Mamani 2020", species="Ammi majus"),
        Row(citation="Jones 2021", species="Carum carvi"),
    ]


def test_duplicate_citation_rows_added_once():
    file_a, path_a = wrap([Row(species="Ammi majus")], citation="Mamani 2020")
    file_b, path_b = wrap([Row(species="Ammi majus")], citation="Mamani 2020")
    result = gather_tablesfiles(
        [(file_a, path_a), (file_b, path_b)], citation_column="citation", key_columns=[]
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [Row(citation="Mamani 2020", species="Ammi majus")]


def test_missing_citation_falls_back_to_filename_stem():
    tablesfile = TablesFile(
        tables=[TableWithFragments(table_fragments=[TableFragment(rows=[Row(species="Ammi majus")], page=1)])],
        citation="",
    )
    path = Path("mamani_2020.tables.json")
    result = gather_tablesfiles([(tablesfile, path)], citation_column="citation", key_columns=[])
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [Row(citation="mamani_2020", species="Ammi majus")]


def test_key_column_sorts_rows():
    file_a, path_a = wrap([Row(species="Zea mays")], citation="Mamani 2020")
    file_b, path_b = wrap([Row(species="Ammi majus")], citation="Jones 2021")
    result = gather_tablesfiles(
        [(file_a, path_a), (file_b, path_b)],
        citation_column="citation",
        key_columns=["species"],
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(citation="Jones 2021", species="Ammi majus"),
        Row(citation="Mamani 2020", species="Zea mays"),
    ]


def test_multiple_tables_in_one_file_collected_flat():
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(table_fragments=[TableFragment(rows=[Row(species="Ammi majus")], page=1)]),
            TableWithFragments(table_fragments=[TableFragment(rows=[Row(species="Carum carvi")], page=2)]),
        ],
        citation="Mamani 2020",
    )
    path = Path("mamani_2020.tables.json")
    result = gather_tablesfiles([(tablesfile, path)], citation_column="citation", key_columns=[])
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(citation="Mamani 2020", species="Ammi majus"),
        Row(citation="Mamani 2020", species="Carum carvi"),
    ]


def test_custom_citation_column_name():
    tablesfile, path = wrap([Row(species="Ammi majus")], citation="Mamani 2020")
    result = gather_tablesfiles([(tablesfile, path)], citation_column="paper", key_columns=[])
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [Row(paper="Mamani 2020", species="Ammi majus")]


def test_path_column_adds_file_path():
    tablesfile, path = wrap([Row(species="Ammi majus")], citation="Mamani 2020")
    result = gather_tablesfiles(
        [(tablesfile, path)], citation_column="citation", key_columns=[], path_column="path"
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(citation="Mamani 2020", path="Mamani 2020.tables.json", species="Ammi majus")
    ]


def test_convergence_rows_keeps_singleton_row_ids():
    tablesfile, path = wrap(
        [Row(species="Ammi majus", row_=1), Row(species="Carum carvi", row_=2)],
        citation="Mamani 2020",
    )
    result = gather_tablesfiles(
        [(tablesfile, path)], citation_column="citation", key_columns=[], convergence="rows"
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(citation="Mamani 2020", species="Ammi majus"),
        Row(citation="Mamani 2020", species="Carum carvi"),
    ]


def test_convergence_rows_excludes_duplicate_row_ids():
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(
                        rows=[
                            Row(species="Ammi majus", row_=1),
                            Row(species="Carum carvi", row_=1),
                            Row(species="Zea mays", row_=2),
                        ],
                        page=1,
                    )
                ]
            )
        ],
        citation="Mamani 2020",
    )
    path = Path("Mamani 2020.tables.json")
    result = gather_tablesfiles(
        [(tablesfile, path)], citation_column="citation", key_columns=[], convergence="rows"
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [Row(citation="Mamani 2020", species="Zea mays")]


def test_convergence_rows_excludes_rows_without_row_id():
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(
                        rows=[Row(species="Ammi majus"), Row(species="Carum carvi", row_=1)],
                        page=1,
                    )
                ]
            )
        ],
        citation="Mamani 2020",
    )
    path = Path("Mamani 2020.tables.json")
    result = gather_tablesfiles(
        [(tablesfile, path)], citation_column="citation", key_columns=[], convergence="rows"
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [Row(citation="Mamani 2020", species="Carum carvi")]


def test_convergence_rows_computed_per_file_not_globally():
    file_a, path_a = wrap([Row(species="Ammi majus", row_=1)], citation="Mamani 2020")
    file_b, path_b = wrap([Row(species="Carum carvi", row_=1)], citation="Jones 2021")
    result = gather_tablesfiles(
        [(file_a, path_a), (file_b, path_b)],
        citation_column="citation",
        key_columns=[],
        convergence="rows",
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(citation="Mamani 2020", species="Ammi majus"),
        Row(citation="Jones 2021", species="Carum carvi"),
    ]


def test_convergence_fragments_includes_fully_convergent_fragments():
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(
                        rows=[Row(species="Ammi majus", row_=1), Row(species="Carum carvi", row_=2)],
                        page=1,
                    )
                ]
            ),
            TableWithFragments(
                table_fragments=[
                    TableFragment(
                        rows=[Row(species="Zea mays", row_=1), Row(species="Zea mays", row_=1)],
                        page=2,
                    )
                ]
            ),
        ],
        citation="Mamani 2020",
    )
    path = Path("Mamani 2020.tables.json")
    result = gather_tablesfiles(
        [(tablesfile, path)], citation_column="citation", key_columns=[], convergence="fragments"
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(citation="Mamani 2020", species="Ammi majus"),
        Row(citation="Mamani 2020", species="Carum carvi"),
    ]


def test_convergence_fragments_excludes_fragment_with_missing_row_id():
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(
                        rows=[Row(species="Ammi majus", row_=1), Row(species="Carum carvi")],
                        page=1,
                    )
                ]
            ),
            TableWithFragments(
                table_fragments=[
                    TableFragment(rows=[Row(species="Zea mays", row_=1)], page=2)
                ]
            ),
        ],
        citation="Mamani 2020",
    )
    path = Path("Mamani 2020.tables.json")
    result = gather_tablesfiles(
        [(tablesfile, path)], citation_column="citation", key_columns=[], convergence="fragments"
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [Row(citation="Mamani 2020", species="Zea mays")]


def test_convergence_tables_includes_fully_convergent_tablesfiles():
    file_a = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(
                        rows=[Row(species="Ammi majus", row_=1), Row(species="Carum carvi", row_=2)],
                        page=1,
                    )
                ]
            )
        ],
        citation="Mamani 2020",
    )
    file_b = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(
                        rows=[Row(species="Zea mays", row_=1), Row(species="Zea mays", row_=1)],
                        page=1,
                    )
                ]
            )
        ],
        citation="Jones 2021",
    )
    path_a = Path("Mamani 2020.tables.json")
    path_b = Path("Jones 2021.tables.json")
    result = gather_tablesfiles(
        [(file_a, path_a), (file_b, path_b)],
        citation_column="citation",
        key_columns=[],
        convergence="tables",
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(citation="Mamani 2020", species="Ammi majus"),
        Row(citation="Mamani 2020", species="Carum carvi"),
    ]


def test_convergence_tables_excludes_non_convergent_tables():
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(rows=[Row(species="Ammi majus", row_=1)], page=1)
                ]
            ),
            TableWithFragments(
                table_fragments=[
                    TableFragment(
                        rows=[Row(species="Zea mays", row_=1), Row(species="Zea mays", row_=1)],
                        page=2,
                    )
                ]
            ),
        ],
        citation="Mamani 2020",
    )
    path = Path("Mamani 2020.tables.json")
    result = gather_tablesfiles(
        [(tablesfile, path)], citation_column="citation", key_columns=[], convergence="tables"
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [Row(citation="Mamani 2020", species="Ammi majus")]


def test_convergence_tables_prints_nothing_when_no_convergent_tables(capsys):
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(
                        rows=[Row(species="Ammi majus", row_=1), Row(species="Carum carvi", row_=1)],
                        page=1,
                    )
                ]
            )
        ],
        citation="Mamani 2020",
    )
    path = Path("Mamani 2020.tables.json")
    gather_tablesfiles(
        [(tablesfile, path)], citation_column="citation", key_columns=[], convergence="tables"
    )
    captured = capsys.readouterr()
    assert captured.out == ""


def test_gather_tablesfiles_prints_row_count_per_file(capsys):
    file_a, path_a = wrap(
        [Row(species="Ammi majus"), Row(species="Carum carvi")], citation="Mamani 2020"
    )
    file_b, path_b = wrap([Row(species="Zea mays")], citation="Jones 2021")
    gather_tablesfiles(
        [(file_a, path_a), (file_b, path_b)], citation_column="citation", key_columns=[]
    )
    captured = capsys.readouterr()
    assert captured.out == "Mamani 2020.tables.json: 2 rows\nJones 2021.tables.json: 1 rows\n"


def test_compute_sources_includes_gathered_files():
    file_a = TablesFile(
        tables=[TableWithFragments(table_fragments=[TableFragment(rows=[Row(species="Ammi majus")], page=1)])],
        citation="Mamani 2020",
        uuid="uuid-a",
    )
    file_b = TablesFile(
        tables=[TableWithFragments(table_fragments=[TableFragment(rows=[Row(species="Carum carvi")], page=1)])],
        citation="Jones 2021",
        uuid="uuid-b",
    )
    path_a = Path("resultset/mamani_2020.tables.json")
    path_b = Path("resultset/jones_2021.tables.json")
    sources = compute_sources([(file_a, path_a), (file_b, path_b)], {})
    assert sources == [
        {"path": "resultset/mamani_2020.tables.json", "uuid": "uuid-a"},
        {"path": "resultset/jones_2021.tables.json", "uuid": "uuid-b"},
    ]


def test_compute_sources_skips_duplicate_citations():
    file_a = TablesFile(
        tables=[TableWithFragments(table_fragments=[TableFragment(rows=[Row(species="Ammi majus")], page=1)])],
        citation="Mamani 2020",
        uuid="uuid-a",
    )
    file_b = TablesFile(
        tables=[TableWithFragments(table_fragments=[TableFragment(rows=[Row(species="Ammi majus")], page=1)])],
        citation="Mamani 2020",
        uuid="uuid-b",
    )
    path_a = Path("resultset_1/mamani_2020.tables.json")
    path_b = Path("resultset_2/mamani_2020.tables.json")
    sources = compute_sources([(file_a, path_a), (file_b, path_b)], {})
    assert sources == [{"path": "resultset_1/mamani_2020.tables.json", "uuid": "uuid-a"}]


def test_compute_sources_includes_reader_from_directory_metadata():
    file_a = TablesFile(
        tables=[TableWithFragments(table_fragments=[TableFragment(rows=[Row(species="Ammi majus")], page=1)])],
        citation="Mamani 2020",
    )
    path_a = Path("resultset/mamani_2020.tables.json")
    directory_metadata = {"resultset": {"reader": "pdfplumber", "uuid": "dir-uuid"}}
    sources = compute_sources([(file_a, path_a)], directory_metadata)
    assert sources == [{"path": "resultset/mamani_2020.tables.json", "reader": "pdfplumber"}]


def test_write_gather_metadata_creates_file(tmp_path):
    sources = [{"path": "resultset/mamani_2020.tables.json", "uuid": "uuid-a"}]
    settings = {"citation_column": "citation", "key_columns": ["species"]}
    write_gather_metadata(tmp_path, sources, settings)
    metadata_file = tmp_path / "tables.metadata.json"
    assert metadata_file.exists()
    metadata = json.loads(metadata_file.read_text())
    assert metadata["reader"] == "tablegather"
    assert metadata["settings"] == {"citation_column": "citation", "key_columns": ["species"]}
    assert metadata["sources"] == [{"path": "resultset/mamani_2020.tables.json", "uuid": "uuid-a"}]
    assert "uuid" in metadata
    assert "datetime" in metadata
