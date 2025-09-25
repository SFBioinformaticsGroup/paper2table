import pytest
from tablestats.stats import compute_paper_stats


def test_empty_paper():
    paper_data = {"tables": []}
    stats = compute_paper_stats(paper_data)
    assert stats["tables"] == 0
    assert stats["rows"] == 0
    assert stats["rows_with_agreement"] == 0
    assert "agreement_percentage" not in stats


def test_paper_with_one_table_one_row():
    paper_data = {"tables": [{"rows": [{"family": "Apiaceae"}]}]}
    stats = compute_paper_stats(paper_data)
    assert stats["tables"] == 1
    assert stats["rows"] == 1
    assert stats["rows_with_agreement"] == 0
    assert "agreement_percentage" in stats
    assert stats["agreement_percentage"] == 0.0


def test_paper_with_agreement_levels():
    paper_data = {
        "tables": [
            {"rows": [
                {"family": "Apiaceae", "_agreement_level": 0},
                {"family": "Rosaceae", "_agreement_level": 2},
                {"family": "Lamiaceae", "_agreement_level": 3},
            ]}
        ]
    }
    stats = compute_paper_stats(paper_data)
    assert stats["tables"] == 1
    assert stats["rows"] == 3
    assert stats["rows_with_agreement"] == 2
    assert pytest.approx(stats["agreement_percentage"], rel=1e-3) == (2 / 3) * 100


def test_multiple_tables():
    paper_data = {
        "tables": [
            {"rows": [{"family": "Apiaceae"}, {"family": "Rosaceae"}]},
            {"rows": [{"family": "Lamiaceae", "_agreement_level": 2}]},
        ]
    }
    stats = compute_paper_stats(paper_data)
    assert stats["tables"] == 2
    assert stats["rows"] == 3
    assert stats["rows_with_agreement"] == 1
    assert stats["agreement_percentage"] == pytest.approx((1 / 3) * 100)
