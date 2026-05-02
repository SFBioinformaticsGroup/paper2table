import json
import pytest
from utils.table_fragments import load_papers


@pytest.fixture
def papers_dir(tmp_path):
    (tmp_path / "paper1.tables.json").write_text(
        json.dumps({"tables": [{"rows": [{"col": "a"}]}]}), encoding="utf-8"
    )
    (tmp_path / "paper2.tables.json").write_text(
        json.dumps({"tables": [{"rows": [{"col": "b"}]}]}), encoding="utf-8"
    )
    return tmp_path


def test_load_papers_returns_all_tables_files(papers_dir):
    papers = load_papers(papers_dir)
    assert set(papers.keys()) == {"paper1.tables.json", "paper2.tables.json"}


def test_load_papers_parses_json(papers_dir):
    papers = load_papers(papers_dir)
    assert papers["paper1.tables.json"]["tables"][0]["rows"][0]["col"] == "a"


def test_load_papers_excludes_metadata(papers_dir):
    (papers_dir / "tables.metadata.json").write_text(
        json.dumps({"meta": "data"}), encoding="utf-8"
    )
    papers = load_papers(papers_dir)
    assert "tables.metadata.json" not in papers


def test_load_papers_empty_directory(tmp_path):
    assert load_papers(tmp_path) == {}
