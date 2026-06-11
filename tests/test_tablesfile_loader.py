import json
import pytest
from pathlib import Path
from tablemerge.tablesfile_loader import TablesFileLoader
from tablemerge.fragment_transformer import FilterTitleRowsTransformer
from tablevalidate.schema import Row, TablesFile


def write_tablesfile(tmp_path: Path, tablesfile: dict) -> Path:
    path = tmp_path / "test.tables.json"
    path.write_text(json.dumps(tablesfile))
    return path


def test_load_returns_tablesfile(tmp_path):
    loader = TablesFileLoader()
    path = write_tablesfile(tmp_path, {
        "tables": [{"table_fragments": [{"rows": [{"species": "Ammi majus"}], "page": 1}]}],
        "citation": None,
    })
    result = loader.load(path)
    assert isinstance(result, TablesFile)


def test_load_applies_filter_title_rows(tmp_path):
    loader = TablesFileLoader(transformers=[FilterTitleRowsTransformer()])
    path = write_tablesfile(tmp_path, {
        "tables": [{"table_fragments": [{"rows": [
            {"0": "Figure 1. Species list"},
            {"0": "Ammi majus", "1": "Apiaceae"},
        ], "page": 1}]}],
        "citation": None,
    })
    result = loader.load(path)
    rows = result.tables[0].get_table_fragments()[0].rows
    assert rows == [Row(**{"0": "Ammi majus", "1": "Apiaceae"})]


def test_load_preserves_rows_without_title(tmp_path):
    loader = TablesFileLoader()
    path = write_tablesfile(tmp_path, {
        "tables": [{"table_fragments": [{"rows": [
            {"0": "Ammi majus", "1": "Apiaceae"},
            {"0": "Rosa canina", "1": "Rosaceae"},
        ], "page": 1}]}],
        "citation": None,
    })
    result = loader.load(path)
    rows = result.tables[0].get_table_fragments()[0].rows
    assert rows == [
        Row(**{"0": "Ammi majus", "1": "Apiaceae"}),
        Row(**{"0": "Rosa canina", "1": "Rosaceae"}),
    ]
