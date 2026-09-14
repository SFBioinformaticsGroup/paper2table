# pyright: reportCallIssue=false

import json
from pathlib import Path

from tablegather.collect import gather_tablesfiles
from tablegather.__main__ import (
    compute_sources,
    write_gather_metadata,
)
from tablevalidate.schema import (
    TablesFile,
    TableFragment,
    TableWithFragments,
    Row,
)


def wrap(rows: list[Row], citation: str = "", page: int = 1) -> tuple[TablesFile, Path]:
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(table_fragments=[TableFragment(rows=rows, page=page)])
        ],
        citation=citation,
    )
    return tablesfile, Path(f"{citation or 'unnamed'}.tables.json")


def test_single_file_adds_citation_and_path_columns():
    tablesfile, path = wrap([Row(species="Ammi majus")], citation="Mamani 2020")
    result = gather_tablesfiles([(tablesfile, path)], key_columns=[])
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(
            citation_="Mamani 2020",
            path_=str(path),
            page_=1,
            fragment_=1,
            species="Ammi majus",
        )
    ]


def test_gathers_two_different_rows():
    file_a, path_a = wrap([Row(species="Ammi majus")], citation="Mamani 2020")
    file_b, path_b = wrap([Row(species="Carum carvi")], citation="Jones 2021")
    result = gather_tablesfiles([(file_a, path_a), (file_b, path_b)], key_columns=[])
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(
            citation_="Mamani 2020",
            path_=str(path_a),
            page_=1,
            fragment_=1,
            species="Ammi majus",
        ),
        Row(
            citation_="Jones 2021",
            path_=str(path_b),
            page_=1,
            fragment_=1,
            species="Carum carvi",
        ),
    ]


def test_duplicate_row_added_once():
    file_a, path_a = wrap([Row(species="Ammi majus")], citation="Mamani 2020")
    file_b, path_b = wrap([Row(species="Ammi majus")], citation="Mamani 2020")
    result = gather_tablesfiles([(file_a, path_a), (file_b, path_b)], key_columns=[])
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(
            citation_="Mamani 2020",
            path_=str(path_a),
            page_=1,
            fragment_=1,
            species="Ammi majus",
        )
    ]


def test_missing_citation_falls_back_to_filename_stem():
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(rows=[Row(species="Ammi majus")], page=1)
                ]
            )
        ],
        citation="",
    )
    path = Path("mamani_2020.tables.json")
    result = gather_tablesfiles([(tablesfile, path)], key_columns=[])
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(
            # FIXME this is wrong. is OK to lack of citation
            citation_="mamani_2020",
            path_=str(path),
            page_=1,
            fragment_=1,
            species="Ammi majus",
        )
    ]


def test_key_column_sorts_rows():
    file_a, path_a = wrap([Row(species="Zea mays")], citation="Mamani 2020")
    file_b, path_b = wrap([Row(species="Ammi majus")], citation="Jones 2021")
    result = gather_tablesfiles(
        [(file_a, path_a), (file_b, path_b)],
        key_columns=["species"],
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(
            citation_="Jones 2021",
            path_=str(path_b),
            page_=1,
            fragment_=1,
            species="Ammi majus",
        ),
        Row(
            citation_="Mamani 2020",
            path_=str(path_a),
            page_=1,
            fragment_=1,
            species="Zea mays",
        ),
    ]


def test_multi_table_file_is_properly_gathered():
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(rows=[Row(species="Ammi majus")], page=1)
                ]
            ),
            TableWithFragments(
                table_fragments=[
                    TableFragment(rows=[Row(species="Carum carvi")], page=2)
                ]
            ),
        ],
        citation="Mamani 2020",
    )
    path = Path("mamani_2020.tables.json")
    result = gather_tablesfiles([(tablesfile, path)], key_columns=[])
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(
            citation_="Mamani 2020",
            path_=str(path),
            page_=1,
            fragment_=1,
            species="Ammi majus",
        ),
        Row(
            citation_="Mamani 2020",
            path_=str(path),
            page_=2,
            fragment_=1,
            species="Carum carvi",
        ),
    ]


def test_multi_fragment_file_is_properly_gathered():
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(rows=[Row(species="Ammi majus")], page=1),
                    TableFragment(rows=[Row(species="Carum carvi")], page=2),
                    TableFragment(rows=[Row(species="Zea mays")], page=2),
                ]
            ),
        ],
        citation="Mamani 2020",
    )
    path = Path("mamani_2020.tables.json")
    result = gather_tablesfiles([(tablesfile, path)], key_columns=[])
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(
            citation_="Mamani 2020",
            path_=str(path),
            page_=1,
            fragment_=1,
            species="Ammi majus",
        ),
        Row(
            citation_="Mamani 2020",
            path_=str(path),
            page_=2,
            fragment_=2,
            species="Carum carvi",
        ),
        Row(
            citation_="Mamani 2020",
            path_=str(path),
            page_=2,
            fragment_=3,
            species="Zea mays",
        ),
    ]


def test_convergence_rows_keeps_singleton_row_ids():
    tablesfile, path = wrap(
        [Row(species="Ammi majus", row_=1), Row(species="Carum carvi", row_=2)],
        citation="Mamani 2020",
    )
    result = gather_tablesfiles(
        [(tablesfile, path)],
        key_columns=[],
        convergence="rows",
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(
            citation_="Mamani 2020",
            path_=str(path),
            page_=1,
            fragment_=1,
            row_=1,
            species="Ammi majus",
        ),
        Row(
            citation_="Mamani 2020",
            path_=str(path),
            page_=1,
            fragment_=1,
            row_=2,
            species="Carum carvi",
        ),
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
        [(tablesfile, path)],
        key_columns=[],
        convergence="rows",
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(
            citation_="Mamani 2020",
            path_=str(path),
            page_=1,
            fragment_=1,
            row_=2,  # original row_
            species="Zea mays",
        )
    ]


def test_convergence_rows_excludes_rows_without_row_id():
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(
                        rows=[
                            Row(species="Ammi majus"),
                            Row(species="Carum carvi", row_=1),
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
        [(tablesfile, path)],
        key_columns=[],
        convergence="rows",
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(
            citation_="Mamani 2020",
            path_=str(path),
            page_=1,
            fragment_=1,
            row_=1,
            species="Carum carvi",
        )
    ]


def test_convergence_rows_computed_per_file_not_globally():
    file_a, path_a = wrap([Row(species="Ammi majus", row_=1)], citation="Mamani 2020")
    file_b, path_b = wrap([Row(species="Carum carvi", row_=1)], citation="Jones 2021")
    result = gather_tablesfiles(
        [(file_a, path_a), (file_b, path_b)],
        key_columns=[],
        convergence="rows",
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(
            citation_="Mamani 2020",
            path_=str(path_a),
            page_=1,
            fragment_=1,
            row_=1,
            species="Ammi majus",
        ),
        Row(
            citation_="Jones 2021",
            path_=str(path_b),
            page_=1,
            fragment_=1,
            row_=1,  # original row_
            species="Carum carvi",
        ),
    ]


def test_convergence_fragments_includes_fully_convergent_fragments():
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(
                        rows=[
                            Row(species="Ammi majus", row_=1),
                            Row(species="Carum carvi", row_=2),
                        ],
                        page=1,
                    )
                ]
            ),
            TableWithFragments(
                table_fragments=[
                    TableFragment(
                        rows=[
                            Row(species="Zea mays", row_=1),
                            Row(species="Zea mays", row_=1),
                        ],
                        page=2,
                    )
                ]
            ),
        ],
        citation="Mamani 2020",
    )
    path = Path("Mamani 2020.tables.json")
    result = gather_tablesfiles(
        [(tablesfile, path)],
        key_columns=[],
        convergence="fragments",
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(
            citation_="Mamani 2020",
            path_=str(path),
            page_=1,
            fragment_=1,
            row_=1,
            species="Ammi majus",
        ),
        Row(
            citation_="Mamani 2020",
            path_=str(path),
            page_=1,
            fragment_=1,
            row_=2,
            species="Carum carvi",
        ),
    ]


def test_convergence_fragments_excludes_fragment_with_missing_row_id():
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(
                        rows=[
                            Row(species="Ammi majus", row_=1),
                            Row(species="Carum carvi"),
                        ],
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
        [(tablesfile, path)],
        key_columns=[],
        convergence="fragments",
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(
            citation_="Mamani 2020",
            path_=str(path),
            page_=2,
            fragment_=1,
            row_=1,
            species="Zea mays",
        )
    ]


def test_convergence_fragments_keeps_1_indexed_fragment_number_of_surviving_fragment():
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    # fragment 1: not convergent, dropped
                    TableFragment(
                        rows=[
                            Row(species="Ammi majus", row_=1),
                            Row(species="Carum carvi", row_=1),
                        ],
                        page=1,
                    ),
                    # fragment 2: convergent, kept - must report fragment_=2,
                    # not fragment_=1, even though it's the only one that
                    # survives
                    TableFragment(rows=[Row(species="Zea mays", row_=1)], page=2),
                ]
            ),
        ],
        citation="Mamani 2020",
    )
    path = Path("Mamani 2020.tables.json")
    result = gather_tablesfiles(
        [(tablesfile, path)],
        key_columns=[],
        convergence="fragments",
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(
            citation_="Mamani 2020",
            path_=str(path),
            page_=2,
            fragment_=2,
            row_=1,
            species="Zea mays",
        )
    ]


def test_convergence_tables_includes_fully_convergent_tablesfiles():
    file_a = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(
                        rows=[
                            Row(species="Ammi majus", row_=1),
                            Row(species="Carum carvi", row_=2),
                        ],
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
                        rows=[
                            Row(species="Zea mays", row_=1),
                            Row(species="Zea mays", row_=1),
                        ],
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
        key_columns=[],
        convergence="tables",
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(
            citation_="Mamani 2020",
            path_=str(path_a),
            page_=1,
            fragment_=1,
            row_=1,
            species="Ammi majus",
        ),
        Row(
            citation_="Mamani 2020",
            path_=str(path_a),
            page_=1,
            fragment_=1,
            row_=2,
            species="Carum carvi",
        ),
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
                        rows=[
                            Row(species="Zea mays", row_=1),
                            Row(species="Zea mays", row_=1),
                        ],
                        page=2,
                    )
                ]
            ),
        ],
        citation="Mamani 2020",
    )
    path = Path("Mamani 2020.tables.json")
    result = gather_tablesfiles(
        [(tablesfile, path)],
        key_columns=[],
        convergence="tables",
    )
    fragments = result.tables[0].get_table_fragments()
    assert fragments[0].rows == [
        Row(
            citation_="Mamani 2020",
            path_=str(path),
            page_=1,
            fragment_=1,
            row_=1,
            species="Ammi majus",
        )
    ]


def test_convergence_tables_prints_nothing_when_no_convergent_tables(capsys):
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(
                        rows=[
                            Row(species="Ammi majus", row_=1),
                            Row(species="Carum carvi", row_=1),
                        ],
                        page=1,
                    )
                ]
            )
        ],
        citation="Mamani 2020",
    )
    path = Path("Mamani 2020.tables.json")
    gather_tablesfiles(
        [(tablesfile, path)],
        key_columns=[],
        convergence="tables",
    )
    captured = capsys.readouterr()
    assert captured.out == ""


def test_gather_tablesfiles_prints_row_count_per_file(capsys):
    file_a, path_a = wrap(
        [Row(species="Ammi majus"), Row(species="Carum carvi")], citation="Mamani 2020"
    )
    file_b, path_b = wrap([Row(species="Zea mays")], citation="Jones 2021")
    gather_tablesfiles([(file_a, path_a), (file_b, path_b)], key_columns=[])
    captured = capsys.readouterr()
    assert (
        captured.out
        == "Mamani 2020.tables.json: 2 rows\nJones 2021.tables.json: 1 rows\n"
    )


def test_compute_sources_includes_gathered_files():
    file_a = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(rows=[Row(species="Ammi majus")], page=1)
                ]
            )
        ],
        citation="Mamani 2020",
        uuid="uuid-a",
    )
    file_b = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(rows=[Row(species="Carum carvi")], page=1)
                ]
            )
        ],
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
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(rows=[Row(species="Ammi majus")], page=1)
                ]
            )
        ],
        citation="Mamani 2020",
        uuid="uuid-a",
    )
    file_b = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(rows=[Row(species="Ammi majus")], page=1)
                ]
            )
        ],
        citation="Mamani 2020",
        uuid="uuid-b",
    )
    path_a = Path("resultset_1/mamani_2020.tables.json")
    path_b = Path("resultset_2/mamani_2020.tables.json")
    sources = compute_sources([(file_a, path_a), (file_b, path_b)], {})
    assert sources == [
        {"path": "resultset_1/mamani_2020.tables.json", "uuid": "uuid-a"}
    ]


def test_compute_sources_includes_reader_from_directory_metadata():
    file_a = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[
                    TableFragment(rows=[Row(species="Ammi majus")], page=1)
                ]
            )
        ],
        citation="Mamani 2020",
    )
    path_a = Path("resultset/mamani_2020.tables.json")
    directory_metadata = {"resultset": {"reader": "pdfplumber", "uuid": "dir-uuid"}}
    sources = compute_sources([(file_a, path_a)], directory_metadata)
    assert sources == [
        {"path": "resultset/mamani_2020.tables.json", "reader": "pdfplumber"}
    ]


def test_write_gather_metadata_creates_file(tmp_path):
    sources = [{"path": "resultset/mamani_2020.tables.json", "uuid": "uuid-a"}]
    settings = {"key_columns": ["species"], "convergence": "none"}
    write_gather_metadata(tmp_path, sources, settings)
    metadata_file = tmp_path / "tables.metadata.json"
    assert metadata_file.exists()
    metadata = json.loads(metadata_file.read_text())
    assert metadata["reader"] == "tablegather"
    assert metadata["settings"] == {
        "key_columns": ["species"],
        "convergence": "none",
    }
    assert metadata["sources"] == [
        {"path": "resultset/mamani_2020.tables.json", "uuid": "uuid-a"}
    ]
    assert "uuid" in metadata
    assert "datetime" in metadata
