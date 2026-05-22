import json

import pytest
from tablevalidate.schema import TablesFile, ValueWithAgreement
from tablestats.stats import compute_paper_stats
from tablestats.__main__ import infer_type, collect_unique_columns, format_stats
from tablestats.stats import GlobalStats


def make_paper(tables):
    return TablesFile.model_validate({"citation": None, "tables": tables})


def test_empty_paper():
    stats = compute_paper_stats(make_paper([]))
    assert stats.tables == 0
    assert stats.rows == 0
    assert stats.rows_with_agreement == 0
    assert stats.agreement_percentage is None


def test_paper_with_one_table_one_row():
    stats = compute_paper_stats(make_paper([{"rows": [{"family": "Apiaceae"}], "page": 1}]))
    assert stats.tables == 1
    assert stats.rows == 1
    assert stats.rows_with_agreement == 0
    assert stats.agreement_percentage == 0.0


def test_paper_with_agreement_levels():
    stats = compute_paper_stats(make_paper([{
        "page": 1,
        "rows": [
            {"family": "Apiaceae", "agreement_level_": 0},
            {"family": "Rosaceae", "agreement_level_": 2},
            {"family": "Lamiaceae", "agreement_level_": 3},
        ],
    }]))
    assert stats.tables == 1
    assert stats.rows == 3
    assert stats.rows_with_agreement == 2
    assert pytest.approx(stats.agreement_percentage, rel=1e-3) == (2 / 3) * 100


def test_multiple_tables():
    stats = compute_paper_stats(make_paper([
        {"page": 1, "rows": [{"family": "Apiaceae"}, {"family": "Rosaceae"}]},
        {"page": 2, "rows": [{"family": "Lamiaceae", "agreement_level_": 2}]},
    ]))
    assert stats.tables == 2
    assert stats.rows == 3
    assert stats.rows_with_agreement == 1
    assert stats.agreement_percentage == pytest.approx((1 / 3) * 100)


def test_infer_type_int():
    assert infer_type("42") == "int"


def test_infer_type_float():
    assert infer_type("3.14") == "float"


def test_infer_type_bool():
    assert infer_type("true") == "bool"
    assert infer_type("False") == "bool"


def test_infer_type_str():
    assert infer_type("Apiaceae") == "str"


def test_infer_type_with_agreement_list():
    assert infer_type([ValueWithAgreement(value="99", agreement_level=2)]) == "int"


def test_format_stats_with_columns():
    stats = GlobalStats(papers=1, tables=1, rows=2, papers_stats={})
    output = format_stats(stats, {"species": "str", "count": "int"})
    assert "Unique Columns:" in output
    assert "species:str" in output
    assert "count:int" in output


def test_format_stats_without_columns():
    stats = GlobalStats(papers=1, tables=1, rows=2, papers_stats={})
    assert "Unique Columns:" not in format_stats(stats)


def test_collect_unique_columns(tmp_path):
    data = {
        "citation": None,
        "tables": [{"page": 1, "rows": [{"species": "Apiaceae", "count": "42", "1": "ignored"}]}],
    }
    (tmp_path / "paper.tables.json").write_text(json.dumps(data))
    columns = collect_unique_columns(str(tmp_path))
    assert columns == {"species": "str", "count": "int"}
    assert "1" not in columns


def test_collect_unique_columns_deduplicates(tmp_path):
    data_a = {
        "citation": None,
        "tables": [{"page": 1, "rows": [{"species": "Apiaceae", "count": "42"}]}],
    }
    data_b = {
        "citation": None,
        "tables": [{"page": 1, "rows": [{"species": "Rosaceae", "count": "100"}]}],
    }
    (tmp_path / "a.tables.json").write_text(json.dumps(data_a))
    (tmp_path / "b.tables.json").write_text(json.dumps(data_b))
    columns = collect_unique_columns(str(tmp_path))
    assert set(columns.keys()) == {"species", "count"}
