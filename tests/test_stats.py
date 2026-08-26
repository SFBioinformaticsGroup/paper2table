import json

import pytest
from tablevalidate.schema import TablesFile, ValueWithAgreement
from tablestats.stats import (
    compute_paper_stats,
    update_papers_stats,
    GlobalStats,
    count_convergent_rows,
    count_shared_values,
    row_value_strings,
)
from tablestats.__main__ import infer_type, collect_unique_columns, format_stats, sort_stats, parse_sort_keys


def make_paper(tables, metadata=None):
    data = {"citation": None, "tables": tables}
    if metadata is not None:
        data["metadata"] = metadata
    return TablesFile.model_validate(data)


def test_empty_paper():
    stats = compute_paper_stats(make_paper([]))
    assert stats.tables == 0
    assert stats.fragments == 0
    assert stats.rows == 0
    assert stats.columns == 0
    assert stats.rows_with_agreement == 0
    assert stats.agreement_percentage is None


def test_paper_with_one_table_one_row():
    stats = compute_paper_stats(
        make_paper([{"rows": [{"family": "Apiaceae"}], "page": 1}])
    )
    assert stats.tables == 1
    assert stats.fragments == 1
    assert stats.rows == 1
    assert stats.columns == 1
    assert stats.rows_with_agreement == 0
    assert stats.agreement_percentage == 0.0


def test_paper_with_agreement_levels():
    stats = compute_paper_stats(
        make_paper(
            [
                {
                    "page": 1,
                    "rows": [
                        {"family": "Apiaceae", "agreement_level_": 0},
                        {"family": "Rosaceae", "agreement_level_": 2},
                        {"family": "Lamiaceae", "agreement_level_": 3},
                    ],
                }
            ]
        )
    )
    assert stats.tables == 1
    assert stats.fragments == 1
    assert stats.rows == 3
    assert stats.columns == 1
    assert stats.rows_with_agreement == 2
    assert pytest.approx(stats.agreement_percentage, rel=1e-3) == (2 / 3) * 100


def test_multiple_tables():
    stats = compute_paper_stats(
        make_paper(
            [
                {"page": 1, "rows": [{"family": "Apiaceae"}, {"family": "Rosaceae"}]},
                {"page": 2, "rows": [{"family": "Lamiaceae", "agreement_level_": 2}]},
            ]
        )
    )
    assert stats.tables == 2
    assert stats.fragments == 2
    assert stats.rows == 3
    assert stats.columns == 1
    assert stats.rows_with_agreement == 1
    assert stats.agreement_percentage == pytest.approx((1 / 3) * 100)


def test_table_with_multiple_fragments_counts_each():
    stats = compute_paper_stats(
        make_paper(
            [
                {
                    "table_fragments": [
                        {"page": 1, "rows": [{"family": "Apiaceae"}]},
                        {"page": 2, "rows": [{"family": "Rosaceae"}]},
                    ]
                }
            ]
        )
    )
    assert stats.tables == 1
    assert stats.fragments == 2
    assert stats.rows == 2


def test_columns_counts_unique_across_fragments():
    stats = compute_paper_stats(
        make_paper(
            [
                {"page": 1, "rows": [{"family": "Apiaceae", "genus": "Ammi"}]},
                {"page": 2, "rows": [{"family": "Rosaceae", "color": "red"}]},
            ]
        )
    )
    assert stats.columns == 3


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
    stats = GlobalStats(
        papers=1,
        tables=1,
        fragments=2,
        rows=2,
        unique_rows=0,
        rows_with_agreement=0,
        rows_in_shared_groups=0,
        rows_with_shared_values=0,
        papers_with_curations=0,
        papers_with_full_convergence=0,
        papers_stats={},
    )
    output = format_stats(stats, {"species": "str", "count": "int"})
    assert "Unique Columns:" in output
    assert "species:str" in output
    assert "count:int" in output


def test_format_stats_without_columns():
    stats = GlobalStats(
        papers=1,
        tables=1,
        fragments=2,
        rows=2,
        unique_rows=0,
        rows_with_agreement=0,
        rows_in_shared_groups=0,
        rows_with_shared_values=0,
        papers_with_curations=0,
        papers_with_full_convergence=0,
        papers_stats={},
    )
    assert "Unique Columns:" not in format_stats(stats)


def test_global_agreement_percentage_no_rows():
    stats = GlobalStats(
        papers=0,
        tables=0,
        fragments=0,
        rows=0,
        unique_rows=0,
        rows_with_agreement=0,
        rows_in_shared_groups=0,
        rows_with_shared_values=0,
        papers_with_curations=0,
        papers_with_full_convergence=0,
        papers_stats={},
    )
    assert stats.global_agreement_percentage is None


def test_global_agreement_percentage_accumulates_across_papers():
    stats = GlobalStats(
        papers=0,
        tables=0,
        fragments=0,
        rows=0,
        unique_rows=0,
        rows_with_agreement=0,
        rows_in_shared_groups=0,
        rows_with_shared_values=0,
        papers_with_curations=0,
        papers_with_full_convergence=0,
        papers_stats={},
    )
    paper_a = make_paper(
        [
            {
                "page": 1,
                "rows": [
                    {"family": "Apiaceae", "agreement_level_": 2},
                    {"family": "Rosaceae", "agreement_level_": 0},
                ],
            }
        ]
    )
    paper_b = make_paper(
        [
            {
                "page": 1,
                "rows": [
                    {"family": "Lamiaceae", "agreement_level_": 3},
                    {"family": "Asteraceae", "agreement_level_": 1},
                ],
            }
        ]
    )
    update_papers_stats(stats, "a.tables.json", paper_a)
    update_papers_stats(stats, "b.tables.json", paper_b)
    assert stats.rows == 4
    assert stats.rows_with_agreement == 2
    assert stats.global_agreement_percentage == pytest.approx(50.0)


def test_format_stats_shows_global_agreement_percentage():
    stats = GlobalStats(
        papers=1,
        tables=1,
        fragments=1,
        rows=4,
        unique_rows=0,
        rows_with_agreement=2,
        rows_in_shared_groups=0,
        rows_with_shared_values=0,
        papers_with_curations=0,
        papers_with_full_convergence=0,
        papers_stats={},
        global_agreement_percentage=50.0,
    )
    output = format_stats(stats)
    assert "Global agreement percentage: 50.00%" in output


def test_format_stats_omits_global_agreement_percentage_when_none():
    stats = GlobalStats(
        papers=0,
        tables=0,
        fragments=0,
        rows=0,
        unique_rows=0,
        rows_with_agreement=0,
        rows_in_shared_groups=0,
        rows_with_shared_values=0,
        papers_with_curations=0,
        papers_with_full_convergence=0,
        papers_stats={},
    )
    assert "Global agreement percentage" not in format_stats(stats)


def test_unique_rows_no_row_attribute():
    stats = compute_paper_stats(
        make_paper(
            [
                {"page": 1, "rows": [{"family": "Apiaceae"}, {"family": "Rosaceae"}]},
            ]
        )
    )
    assert stats.unique_rows == 0


def test_unique_rows_single_table():
    stats = compute_paper_stats(
        make_paper(
            [
                {
                    "page": 1,
                    "rows": [
                        {"family": "Apiaceae", "row_": 1},
                        {"family": "Rosaceae", "row_": 1},
                        {"family": "Lamiaceae", "row_": 2},
                        {"family": "Asteraceae", "row_": 2},
                        {"family": "Fabaceae", "row_": 2},
                    ],
                }
            ]
        )
    )
    assert stats.unique_rows == 2


def test_unique_rows_multiple_tables():
    stats = compute_paper_stats(
        make_paper(
            [
                {
                    "page": 1,
                    "rows": [
                        {"family": "Apiaceae", "row_": 1},
                        {"family": "Rosaceae", "row_": 1},
                        {"family": "Lamiaceae", "row_": 2},
                        {"family": "Asteraceae", "row_": 2},
                        {"family": "Fabaceae", "row_": 2},
                    ],
                },
                {
                    "page": 2,
                    "rows": [
                        {"family": "Poaceae", "row_": 1},
                        {"family": "Cyperaceae", "row_": 2},
                        {"family": "Orchidaceae", "row_": 3},
                        {"family": "Bromeliaceae", "row_": 4},
                    ],
                },
            ]
        )
    )
    assert stats.unique_rows == 6


def test_unique_rows_across_fragments():
    stats = compute_paper_stats(
        make_paper(
            [
                {
                    "table_fragments": [
                        {
                            "page": 1,
                            "rows": [
                                {"family": "Apiaceae", "row_": 1},
                                {"family": "Rosaceae", "row_": 2},
                            ],
                        },
                        {
                            "page": 2,
                            "rows": [
                                {"family": "Lamiaceae", "row_": 2},
                                {"family": "Asteraceae", "row_": 3},
                            ],
                        },
                    ]
                }
            ]
        )
    )
    assert stats.unique_rows == 3


def test_collect_unique_columns(tmp_path):
    data = {
        "citation": None,
        "tables": [
            {
                "page": 1,
                "rows": [{"species": "Apiaceae", "count": "42", "1": "ignored"}],
            }
        ],
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


def test_row_value_strings_plain_strings():
    paper = make_paper(
        [{"page": 1, "rows": [{"family": "Apiaceae", "genus": "Ammi", "row_": 1}]}]
    )
    row = paper.tables[0].get_table_fragments()[0].rows[0]
    assert row_value_strings(row) == frozenset(
        {("family", "Apiaceae"), ("genus", "Ammi")}
    )


def test_row_value_strings_agreement_list():
    paper = make_paper(
        [
            {
                "page": 1,
                "rows": [
                    {"family": [{"value": "Apiaceae", "agreement_level": 2}], "row_": 1}
                ],
            }
        ]
    )
    row = paper.tables[0].get_table_fragments()[0].rows[0]
    assert row_value_strings(row) == frozenset({("family", "Apiaceae")})


def test_row_value_strings_skips_empty():
    paper = make_paper(
        [{"page": 1, "rows": [{"family": "", "genus": "Ammi", "row_": 1}]}]
    )
    row = paper.tables[0].get_table_fragments()[0].rows[0]
    assert row_value_strings(row) == frozenset({("genus", "Ammi")})


def test_row_value_strings_skips_none():
    paper = make_paper(
        [{"page": 1, "rows": [{"family": None, "genus": "Ammi", "row_": 1}]}]
    )
    row = paper.tables[0].get_table_fragments()[0].rows[0]
    assert row_value_strings(row) == frozenset({("genus", "Ammi")})


def test_count_shared_values_example_from_spec():
    # row_ 1: "v 1" vs "v 2" — no shared value; row_ 2: "v 3" vs "v 3" — shared
    paper = make_paper(
        [
            {
                "page": 1,
                "rows": [
                    {"family": "v 1", "row_": 1},
                    {"family": "v 2", "row_": 1},
                    {"family": "v 3", "row_": 2},
                    {"family": "v 3", "row_": 2},
                ],
            }
        ]
    )
    rows_in_groups, rows_with_shared_values = count_shared_values(paper.tables)
    assert rows_in_groups == 4
    assert rows_with_shared_values == 2


def test_count_shared_values_all_shared():
    paper = make_paper(
        [
            {
                "page": 1,
                "rows": [
                    {"family": "Apiaceae", "row_": 1},
                    {"family": "Apiaceae", "row_": 1},
                    {"family": "Rosaceae", "row_": 2},
                    {"family": "Rosaceae", "row_": 2},
                ],
            }
        ]
    )
    rows_in_groups, rows_with_shared_values = count_shared_values(paper.tables)
    assert rows_in_groups == 4
    assert rows_with_shared_values == 4


def test_count_shared_values_none_shared():
    paper = make_paper(
        [
            {
                "page": 1,
                "rows": [
                    {"family": "Apiaceae", "row_": 1},
                    {"family": "Rosaceae", "row_": 1},
                    {"family": "Lamiaceae", "row_": 2},
                    {"family": "Asteraceae", "row_": 2},
                ],
            }
        ]
    )
    rows_in_groups, rows_with_shared_values = count_shared_values(paper.tables)
    assert rows_in_groups == 4
    assert rows_with_shared_values == 0


def test_count_shared_values_ignores_singletons():
    paper = make_paper(
        [
            {
                "page": 1,
                "rows": [
                    {"family": "Apiaceae", "row_": 1},
                    {"family": "Rosaceae", "row_": 2},
                    {"family": "Lamiaceae", "row_": 3},
                ],
            }
        ]
    )
    rows_in_groups, rows_with_shared_values = count_shared_values(paper.tables)
    assert rows_in_groups == 0
    assert rows_with_shared_values == 0


def test_count_shared_values_ignores_rows_without_row_():
    paper = make_paper(
        [
            {
                "page": 1,
                "rows": [
                    {"family": "Apiaceae"},
                    {"family": "Apiaceae"},
                ],
            }
        ]
    )
    rows_in_groups, rows_with_shared_values = count_shared_values(paper.tables)
    assert rows_in_groups == 0
    assert rows_with_shared_values == 0


def test_count_shared_values_across_fragments():
    paper = make_paper(
        [
            {
                "table_fragments": [
                    {"page": 1, "rows": [{"family": "Apiaceae", "row_": 1}]},
                    {"page": 2, "rows": [{"family": "Apiaceae", "row_": 1}]},
                ]
            }
        ]
    )
    rows_in_groups, rows_with_shared_values = count_shared_values(paper.tables)
    assert rows_in_groups == 2
    assert rows_with_shared_values == 2


def test_count_shared_values_independent_per_table():
    paper = make_paper(
        [
            {
                "page": 1,
                "rows": [
                    {"family": "Apiaceae", "row_": 1},
                    {"family": "Apiaceae", "row_": 1},
                ],
            },
            {
                "page": 2,
                "rows": [
                    {"family": "Rosaceae", "row_": 1},
                    {"family": "Asteraceae", "row_": 1},
                ],
            },
        ]
    )
    rows_in_groups, rows_with_shared_values = count_shared_values(paper.tables)
    assert rows_in_groups == 4
    assert rows_with_shared_values == 2


def test_shared_values_percentage_in_paper_stats():
    stats = compute_paper_stats(
        make_paper(
            [
                {
                    "page": 1,
                    "rows": [
                        {"family": "v 1", "row_": 1},
                        {"family": "v 2", "row_": 1},
                        {"family": "v 3", "row_": 2},
                        {"family": "v 3", "row_": 2},
                    ],
                }
            ]
        )
    )
    assert stats.rows_in_shared_groups == 4
    assert stats.rows_with_shared_values == 2
    assert stats.shared_values_percentage == pytest.approx(50.0)


def test_shared_values_percentage_none_when_no_shared_groups():
    stats = compute_paper_stats(
        make_paper(
            [
                {
                    "page": 1,
                    "rows": [
                        {"family": "Apiaceae", "row_": 1},
                        {"family": "Rosaceae", "row_": 2},
                    ],
                }
            ]
        )
    )
    assert stats.rows_in_shared_groups == 0
    assert stats.shared_values_percentage is None


def test_global_shared_values_percentage_accumulates():
    stats = GlobalStats(
        papers=0,
        tables=0,
        fragments=0,
        rows=0,
        unique_rows=0,
        rows_with_agreement=0,
        rows_in_shared_groups=0,
        rows_with_shared_values=0,
        papers_with_curations=0,
        papers_with_full_convergence=0,
        papers_stats={},
    )
    paper_a = make_paper(
        [
            {
                "page": 1,
                "rows": [
                    {"family": "v 1", "row_": 1},
                    {"family": "v 2", "row_": 1},
                ],
            }
        ]
    )
    paper_b = make_paper(
        [
            {
                "page": 1,
                "rows": [
                    {"family": "v 3", "row_": 1},
                    {"family": "v 3", "row_": 1},
                ],
            }
        ]
    )
    update_papers_stats(stats, "a.tables.json", paper_a)
    update_papers_stats(stats, "b.tables.json", paper_b)
    assert stats.rows_in_shared_groups == 4
    assert stats.rows_with_shared_values == 2
    assert stats.global_shared_values_percentage == pytest.approx(50.0)


def test_global_shared_values_percentage_none_when_no_groups():
    stats = GlobalStats(
        papers=0,
        tables=0,
        fragments=0,
        rows=0,
        unique_rows=0,
        rows_with_agreement=0,
        rows_in_shared_groups=0,
        rows_with_shared_values=0,
        papers_with_curations=0,
        papers_with_full_convergence=0,
        papers_stats={},
    )
    paper = make_paper([{"page": 1, "rows": [{"family": "Apiaceae", "row_": 1}]}])
    update_papers_stats(stats, "a.tables.json", paper)
    assert stats.global_shared_values_percentage is None


def test_format_stats_shows_global_shared_values_percentage():
    stats = GlobalStats(
        papers=1,
        tables=1,
        fragments=1,
        rows=4,
        unique_rows=0,
        rows_with_agreement=0,
        rows_in_shared_groups=4,
        rows_with_shared_values=2,
        papers_with_curations=0,
        papers_with_full_convergence=0,
        papers_stats={},
        global_shared_values_percentage=50.0,
    )
    assert "Global shared values percentage: 50.00%" in format_stats(stats)


def test_format_stats_omits_global_shared_values_percentage_when_none():
    stats = GlobalStats(
        papers=0,
        tables=0,
        fragments=0,
        rows=0,
        unique_rows=0,
        rows_with_agreement=0,
        rows_in_shared_groups=0,
        rows_with_shared_values=0,
        papers_with_curations=0,
        papers_with_full_convergence=0,
        papers_stats={},
    )
    assert "Global shared values percentage" not in format_stats(stats)


def test_paper_with_curations():
    stats = compute_paper_stats(
        make_paper(
            [{"page": 1, "rows": [{"family": "Apiaceae"}]}],
            metadata={"filename": "paper.pdf", "curations": [{"curator": "Alice"}, {"curator": "Bob"}]},
        )
    )
    assert stats.curations == 2


def test_paper_without_curations():
    stats = compute_paper_stats(make_paper([{"page": 1, "rows": [{"family": "Apiaceae"}]}]))
    assert stats.curations == 0


def test_paper_with_empty_curations_list():
    stats = compute_paper_stats(
        make_paper(
            [{"page": 1, "rows": [{"family": "Apiaceae"}]}],
            metadata={"filename": "paper.pdf", "curations": []},
        )
    )
    assert stats.curations == 0


def test_convergent_rows_all_unique():
    stats = compute_paper_stats(
        make_paper(
            [
                {
                    "page": 1,
                    "rows": [
                        {"family": "Apiaceae", "row_": 1},
                        {"family": "Rosaceae", "row_": 2},
                        {"family": "Lamiaceae", "row_": 3},
                    ],
                }
            ]
        )
    )
    assert stats.convergent_rows_percentage == 100.0


def test_convergent_rows_some_duplicate():
    stats = compute_paper_stats(
        make_paper(
            [
                {
                    "page": 1,
                    "rows": [
                        {"family": "Apiaceae", "row_": 1},
                        {"family": "Rosaceae", "row_": 1},
                        {"family": "Lamiaceae", "row_": 2},
                    ],
                }
            ]
        )
    )
    assert stats.convergent_rows_percentage == pytest.approx(1 / 3 * 100)


def test_convergent_rows_no_row_id():
    stats = compute_paper_stats(
        make_paper([{"page": 1, "rows": [{"family": "Apiaceae"}, {"family": "Rosaceae"}]}])
    )
    assert stats.convergent_rows_percentage is None


def test_count_convergent_rows_all_singleton_groups():
    paper = make_paper(
        [
            {
                "page": 1,
                "rows": [
                    {"family": "Apiaceae", "row_": 1},
                    {"family": "Rosaceae", "row_": 2},
                ],
            }
        ]
    )
    convergent_groups, total_rows_with_row_id = count_convergent_rows(paper.tables)
    assert convergent_groups == 2
    assert total_rows_with_row_id == 2


def test_count_convergent_rows_groups_independent_per_table():
    paper = make_paper(
        [
            {"page": 1, "rows": [{"family": "Apiaceae", "row_": 1}, {"family": "Rosaceae", "row_": 1}]},
            {"page": 2, "rows": [{"family": "Lamiaceae", "row_": 1}]},
        ]
    )
    convergent_groups, total_rows_with_row_id = count_convergent_rows(paper.tables)
    assert convergent_groups == 1
    assert total_rows_with_row_id == 3


def test_update_papers_stats_counts_papers_with_curations():
    stats = GlobalStats(
        papers=0,
        tables=0,
        fragments=0,
        rows=0,
        unique_rows=0,
        rows_with_agreement=0,
        rows_in_shared_groups=0,
        rows_with_shared_values=0,
        papers_with_curations=0,
        papers_with_full_convergence=0,
        papers_stats={},
    )
    paper_with_curations = make_paper(
        [{"page": 1, "rows": [{"family": "Apiaceae"}]}],
        metadata={"filename": "a.pdf", "curations": [{"curator": "Alice"}]},
    )
    paper_without_curations = make_paper([{"page": 1, "rows": [{"family": "Rosaceae"}]}])
    update_papers_stats(stats, "a.tables.json", paper_with_curations)
    update_papers_stats(stats, "b.tables.json", paper_without_curations)
    assert stats.papers_with_curations == 1


def test_update_papers_stats_counts_papers_with_full_convergence():
    stats = GlobalStats(
        papers=0,
        tables=0,
        fragments=0,
        rows=0,
        unique_rows=0,
        rows_with_agreement=0,
        rows_in_shared_groups=0,
        rows_with_shared_values=0,
        papers_with_curations=0,
        papers_with_full_convergence=0,
        papers_stats={},
    )
    paper_full_convergence = make_paper(
        [{"page": 1, "rows": [{"family": "Apiaceae", "row_": 1}, {"family": "Rosaceae", "row_": 2}]}]
    )
    paper_partial_convergence = make_paper(
        [{"page": 1, "rows": [{"family": "Apiaceae", "row_": 1}, {"family": "Rosaceae", "row_": 1}]}]
    )
    update_papers_stats(stats, "a.tables.json", paper_full_convergence)
    update_papers_stats(stats, "b.tables.json", paper_partial_convergence)
    assert stats.papers_with_full_convergence == 1


def test_format_stats_shows_curations_and_convergence():
    stats = GlobalStats(
        papers=1,
        tables=1,
        fragments=1,
        rows=2,
        unique_rows=2,
        rows_with_agreement=0,
        rows_in_shared_groups=0,
        rows_with_shared_values=0,
        papers_with_curations=1,
        papers_with_full_convergence=1,
        papers_stats={
            "paper.tables.json": compute_paper_stats(
                make_paper(
                    [{"page": 1, "rows": [{"family": "Apiaceae", "row_": 1}]}],
                    metadata={"filename": "paper.pdf", "curations": [{"curator": "Alice"}]},
                )
            )
        },
    )
    output = format_stats(stats)
    assert "Papers with curations: 1" in output
    assert "Papers with full convergence: 1" in output
    assert "Curations: 1" in output
    assert "Convergent rows percentage: 100.00%" in output


def make_global_stats_with_papers(papers_stats: dict) -> GlobalStats:
    stats = GlobalStats(
        papers=len(papers_stats),
        tables=0,
        fragments=0,
        rows=0,
        unique_rows=0,
        rows_with_agreement=0,
        rows_in_shared_groups=0,
        rows_with_shared_values=0,
        papers_with_curations=0,
        papers_with_full_convergence=0,
        papers_stats=papers_stats,
    )
    return stats


def test_parse_sort_keys_empty():
    assert parse_sort_keys(None) == []


def test_parse_sort_keys_single_defaults_to_asc():
    assert parse_sort_keys("tables-count") == [("tables-count", "asc")]


def test_parse_sort_keys_explicit_asc():
    assert parse_sort_keys("tables-count:asc") == [("tables-count", "asc")]


def test_parse_sort_keys_explicit_desc():
    assert parse_sort_keys("curations-count:desc") == [("curations-count", "desc")]


def test_parse_sort_keys_multiple_with_directions():
    assert parse_sort_keys("tables-count,rows-convergence:asc,curations-count:desc") == [
        ("tables-count", "asc"),
        ("rows-convergence", "asc"),
        ("curations-count", "desc"),
    ]


def test_parse_sort_keys_strips_spaces():
    assert parse_sort_keys("tables-count, curations-count:desc") == [
        ("tables-count", "asc"),
        ("curations-count", "desc"),
    ]


def test_parse_sort_keys_invalid_key_exits():
    with pytest.raises(SystemExit):
        parse_sort_keys("unknown-key")


def test_parse_sort_keys_invalid_direction_exits():
    with pytest.raises(SystemExit):
        parse_sort_keys("tables-count:sideways")


def test_sort_stats_by_tables_count_asc():
    paper_a = compute_paper_stats(
        make_paper([{"page": 1, "rows": [{"family": "Apiaceae"}]}, {"page": 2, "rows": [{"family": "Rosaceae"}]}])
    )
    paper_b = compute_paper_stats(make_paper([{"page": 1, "rows": [{"family": "Lamiaceae"}]}]))
    stats = make_global_stats_with_papers({"a.tables.json": paper_a, "b.tables.json": paper_b})
    sort_stats(stats, [("tables-count", "asc")])
    assert list(stats.papers_stats.keys()) == ["b.tables.json", "a.tables.json"]


def test_sort_stats_by_tables_count_desc():
    paper_a = compute_paper_stats(
        make_paper([{"page": 1, "rows": [{"family": "Apiaceae"}]}, {"page": 2, "rows": [{"family": "Rosaceae"}]}])
    )
    paper_b = compute_paper_stats(make_paper([{"page": 1, "rows": [{"family": "Lamiaceae"}]}]))
    stats = make_global_stats_with_papers({"a.tables.json": paper_a, "b.tables.json": paper_b})
    sort_stats(stats, [("tables-count", "desc")])
    assert list(stats.papers_stats.keys()) == ["a.tables.json", "b.tables.json"]


def test_sort_stats_by_curations_count_asc():
    paper_a = compute_paper_stats(
        make_paper(
            [{"page": 1, "rows": [{"family": "Apiaceae"}]}],
            metadata={"filename": "a.pdf", "curations": [{"curator": "Alice"}, {"curator": "Bob"}]},
        )
    )
    paper_b = compute_paper_stats(
        make_paper(
            [{"page": 1, "rows": [{"family": "Rosaceae"}]}],
            metadata={"filename": "b.pdf", "curations": [{"curator": "Carol"}]},
        )
    )
    stats = make_global_stats_with_papers({"a.tables.json": paper_a, "b.tables.json": paper_b})
    sort_stats(stats, [("curations-count", "asc")])
    assert list(stats.papers_stats.keys()) == ["b.tables.json", "a.tables.json"]


def test_sort_stats_by_curations_count_desc():
    paper_a = compute_paper_stats(
        make_paper(
            [{"page": 1, "rows": [{"family": "Apiaceae"}]}],
            metadata={"filename": "a.pdf", "curations": [{"curator": "Alice"}, {"curator": "Bob"}]},
        )
    )
    paper_b = compute_paper_stats(
        make_paper(
            [{"page": 1, "rows": [{"family": "Rosaceae"}]}],
            metadata={"filename": "b.pdf", "curations": [{"curator": "Carol"}]},
        )
    )
    stats = make_global_stats_with_papers({"a.tables.json": paper_a, "b.tables.json": paper_b})
    sort_stats(stats, [("curations-count", "desc")])
    assert list(stats.papers_stats.keys()) == ["a.tables.json", "b.tables.json"]


def test_sort_stats_by_rows_convergence_asc():
    paper_a = compute_paper_stats(
        make_paper(
            [{"page": 1, "rows": [{"family": "Apiaceae", "row_": 1}, {"family": "Rosaceae", "row_": 1}]}]
        )
    )
    paper_b = compute_paper_stats(
        make_paper(
            [{"page": 1, "rows": [{"family": "Lamiaceae", "row_": 1}, {"family": "Asteraceae", "row_": 2}]}]
        )
    )
    stats = make_global_stats_with_papers({"a.tables.json": paper_a, "b.tables.json": paper_b})
    sort_stats(stats, [("rows-convergence", "asc")])
    assert list(stats.papers_stats.keys()) == ["a.tables.json", "b.tables.json"]


def test_sort_stats_by_rows_convergence_desc():
    paper_a = compute_paper_stats(
        make_paper(
            [{"page": 1, "rows": [{"family": "Apiaceae", "row_": 1}, {"family": "Rosaceae", "row_": 1}]}]
        )
    )
    paper_b = compute_paper_stats(
        make_paper(
            [{"page": 1, "rows": [{"family": "Lamiaceae", "row_": 1}, {"family": "Asteraceae", "row_": 2}]}]
        )
    )
    stats = make_global_stats_with_papers({"a.tables.json": paper_a, "b.tables.json": paper_b})
    sort_stats(stats, [("rows-convergence", "desc")])
    assert list(stats.papers_stats.keys()) == ["b.tables.json", "a.tables.json"]


def test_sort_stats_by_rows_convergence_none_last_asc():
    paper_a = compute_paper_stats(
        make_paper([{"page": 1, "rows": [{"family": "Apiaceae"}]}])
    )
    paper_b = compute_paper_stats(
        make_paper([{"page": 1, "rows": [{"family": "Lamiaceae", "row_": 1}]}])
    )
    stats = make_global_stats_with_papers({"a.tables.json": paper_a, "b.tables.json": paper_b})
    sort_stats(stats, [("rows-convergence", "asc")])
    assert list(stats.papers_stats.keys()) == ["b.tables.json", "a.tables.json"]


def test_sort_stats_by_rows_convergence_none_last_desc():
    paper_a = compute_paper_stats(
        make_paper([{"page": 1, "rows": [{"family": "Apiaceae"}]}])
    )
    paper_b = compute_paper_stats(
        make_paper([{"page": 1, "rows": [{"family": "Lamiaceae", "row_": 1}]}])
    )
    stats = make_global_stats_with_papers({"a.tables.json": paper_a, "b.tables.json": paper_b})
    sort_stats(stats, [("rows-convergence", "desc")])
    assert list(stats.papers_stats.keys()) == ["b.tables.json", "a.tables.json"]


def test_sort_stats_additive():
    paper_a = compute_paper_stats(
        make_paper(
            [{"page": 1, "rows": [{"family": "Apiaceae"}]}],
            metadata={"filename": "a.pdf", "curations": [{"curator": "Alice"}]},
        )
    )
    paper_b = compute_paper_stats(
        make_paper(
            [{"page": 1, "rows": [{"family": "Rosaceae"}]}],
            metadata={"filename": "b.pdf", "curations": [{"curator": "Bob"}]},
        )
    )
    paper_c = compute_paper_stats(
        make_paper(
            [{"page": 1, "rows": [{"family": "Lamiaceae"}]}, {"page": 2, "rows": [{"family": "Asteraceae"}]}],
            metadata={"filename": "c.pdf", "curations": [{"curator": "Carol"}]},
        )
    )
    stats = make_global_stats_with_papers(
        {"a.tables.json": paper_a, "b.tables.json": paper_b, "c.tables.json": paper_c}
    )
    sort_stats(stats, [("tables-count", "asc"), ("curations-count", "asc")])
    keys = list(stats.papers_stats.keys())
    assert keys.index("c.tables.json") > keys.index("a.tables.json")
    assert keys.index("c.tables.json") > keys.index("b.tables.json")


def test_sort_stats_no_keys_preserves_order():
    paper_a = compute_paper_stats(make_paper([{"page": 1, "rows": [{"family": "Apiaceae"}]}]))
    paper_b = compute_paper_stats(make_paper([{"page": 1, "rows": [{"family": "Rosaceae"}]}]))
    stats = make_global_stats_with_papers({"a.tables.json": paper_a, "b.tables.json": paper_b})
    sort_stats(stats, [])
    assert list(stats.papers_stats.keys()) == ["a.tables.json", "b.tables.json"]
