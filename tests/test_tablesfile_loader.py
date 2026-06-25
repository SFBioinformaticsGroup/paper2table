# pyright: reportArgumentType=false
# pyright: reportCallIssue=false
import json
from pathlib import Path
from tablemerge.tablesfile_loader import TablesFileLoader
from tablemerge.fragment_transformer import (
    FilterEmptyRowsTransformer,
    FilterTitleRowsTransformer,
)
from tablemerge.fragments_compactor import SafeConsecutiveFragmentsCompactor
from tablevalidate.schema import Row, TablesFile, TableWithFragments, TableFragment


def write_tablesfile(tmp_path: Path, tablesfile: dict) -> Path:
    path = tmp_path / "test.tables.json"
    path.write_text(json.dumps(tablesfile))
    return path


def test_load_returns_tablesfile(tmp_path):
    loader = TablesFileLoader()
    path = write_tablesfile(
        tmp_path,
        {
            "tables": [
                {"table_fragments": [{"rows": [{"species": "Ammi majus"}], "page": 1}]}
            ],
            "citation": None,
        },
    )
    result = loader.load(path)
    assert isinstance(result, TablesFile)


def test_load_applies_filter_title_rows(tmp_path):
    loader = TablesFileLoader(pretransformers=[FilterTitleRowsTransformer()])
    path = write_tablesfile(
        tmp_path,
        {
            "tables": [
                {
                    "table_fragments": [
                        {
                            "rows": [
                                {"0": "Figure 1. Species list"},
                                {"0": "Ammi majus", "1": "Apiaceae"},
                            ],
                            "page": 1,
                        }
                    ]
                }
            ],
            "citation": None,
        },
    )
    result = loader.load(path)
    rows = result.tables[0].get_table_fragments()[0].rows
    assert rows == [Row(**{"0": "Ammi majus", "1": "Apiaceae"})]


def test_load_applies_compactor(tmp_path):
    loader = TablesFileLoader(compactor=SafeConsecutiveFragmentsCompactor())
    path = write_tablesfile(
        tmp_path,
        {
            "tables": [
                {"table_fragments": [{"rows": [{"species": "Ammi majus"}], "page": 1}]},
                {
                    "table_fragments": [
                        {"rows": [{"species": "Rosa canina"}], "page": 2}
                    ]
                },
            ],
            "citation": None,
        },
    )
    result = loader.load(path)
    assert result.tables == [
        TableWithFragments(
            table_fragments=[
                TableFragment(rows=[Row(species="Ammi majus")], page=1),
                TableFragment(rows=[Row(species="Rosa canina")], page=2),
            ]
        )
    ]


def test_load_applies_filter_empty_rows(tmp_path):
    loader = TablesFileLoader(pretransformers=[FilterEmptyRowsTransformer()])
    path = write_tablesfile(
        tmp_path,
        {
            "tables": [
                {
                    "table_fragments": [
                        {
                            "rows": [
                                {"0": ""},
                                {"0": "Ammi majus", "1": "Apiaceae"},
                                {"0": "", "1": ""},
                            ],
                            "page": 1,
                        }
                    ]
                }
            ],
            "citation": None,
        },
    )
    result = loader.load(path)
    rows = result.tables[0].get_table_fragments()[0].rows
    assert rows == [Row(**{"0": "Ammi majus", "1": "Apiaceae"})]


def test_load_preserves_rows_without_title(tmp_path):
    loader = TablesFileLoader()
    path = write_tablesfile(
        tmp_path,
        {
            "tables": [
                {
                    "table_fragments": [
                        {
                            "rows": [
                                {"0": "Ammi majus", "1": "Apiaceae"},
                                {"0": "Rosa canina", "1": "Rosaceae"},
                            ],
                            "page": 1,
                        }
                    ]
                }
            ],
            "citation": None,
        },
    )
    result = loader.load(path)
    rows = result.tables[0].get_table_fragments()[0].rows
    assert rows == [
        Row(**{"0": "Ammi majus", "1": "Apiaceae"}),
        Row(**{"0": "Rosa canina", "1": "Rosaceae"}),
    ]
