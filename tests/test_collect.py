import json
from pathlib import Path

from tablegather.collect import gather_tablesfiles
from tablegather.__main__ import compute_sources, write_gather_metadata
from tablegather.schema import parse_schema_with_keys
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


def test_parse_schema_with_keys_extracts_key_columns():
    schema, key_columns = parse_schema_with_keys("species:str:key compound:str")
    assert key_columns == ["species"]
    assert list(schema.keys()) == ["species", "compound"]


def test_parse_schema_with_keys_no_keys():
    schema, key_columns = parse_schema_with_keys("species:str compound:str")
    assert key_columns == []
    assert list(schema.keys()) == ["species", "compound"]


def test_parse_schema_with_keys_multiple_keys():
    schema, key_columns = parse_schema_with_keys("species:str:key compound:str:key value:int")
    assert key_columns == ["species", "compound"]
    assert list(schema.keys()) == ["species", "compound", "value"]


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
