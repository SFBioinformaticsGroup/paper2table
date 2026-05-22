# pyright: reportCallIssue=false
# pyright: reportArgumentType=false
import logging
from unittest.mock import patch

import pytest

from tablemerge.analyzers import AliasAnalyzer, JaccardAnalyzer, SemanticAnalyzer
from tablevalidate.schema import Row, TableFragment


def wrap(rows: list[Row]) -> TableFragment:
    return TableFragment(rows=rows, page=1)


def cols(fragment: TableFragment) -> list[str]:
    return list(dict.fromkeys(c for row in fragment.rows for c in row.get_columns()))


def test_jaccard_numeric_to_semantic():
    left = wrap([Row(**{"family": "Apiaceae"}), Row(**{"family": "Rosaceae"})])
    right = wrap([Row(**{"0": "Apiaceae"}), Row(**{"0": "Rosaceae"})])
    result = JaccardAnalyzer().build_mapping(
        cols(left), cols(right), left.rows, right.rows
    )
    assert result == {"0": "family"}


def test_jaccard_both_semantic_returns_empty():
    left = wrap([Row(**{"family": "Apiaceae"})])
    right = wrap([Row(**{"genus": "Ammi"})])
    result = JaccardAnalyzer().build_mapping(
        cols(left), cols(right), left.rows, right.rows
    )
    assert result == {}


def test_jaccard_no_overlap_returns_empty():
    left = wrap([Row(**{"family": "Apiaceae"})])
    right = wrap([Row(**{"0": "red"})])
    result = JaccardAnalyzer().build_mapping(
        cols(left), cols(right), left.rows, right.rows
    )
    assert result == {}


def test_jaccard_threshold_respected():
    left = wrap([Row(**{"family": "Apiaceae"}), Row(**{"family": "Rosaceae"})])
    right = wrap([Row(**{"0": "Apiaceae"})])
    assert JaccardAnalyzer(threshold=0.5).build_mapping(
        cols(left), cols(right), left.rows, right.rows
    ) == {"0": "family"}
    assert (
        JaccardAnalyzer(threshold=0.6).build_mapping(
            cols(left), cols(right), left.rows, right.rows
        )
        == {}
    )


def test_alias_applies_known_alias():
    left = wrap([Row(**{"familia": "Apiaceae"})])
    right = wrap([Row(**{"family": "Apiaceae"})])
    result = AliasAnalyzer({"familia": "family"}).build_mapping(
        cols(left), cols(right), left.rows, right.rows
    )
    assert result == {"familia": "family"}


def test_alias_ignores_unknown_cols():
    left = wrap([Row(**{"genus": "Ammi"})])
    right = wrap([Row(**{"family": "Apiaceae"})])
    result = AliasAnalyzer({"familia": "family"}).build_mapping(
        cols(left), cols(right), left.rows, right.rows
    )
    assert result == {}


def test_alias_maps_both_left_and_right():
    left = wrap([Row(**{"familia": "Apiaceae"})])
    right = wrap([Row(**{"especie": "Ammi majus"})])
    result = AliasAnalyzer({"familia": "family", "especie": "species"}).build_mapping(
        cols(left), cols(right), left.rows, right.rows
    )
    assert result == {"familia": "family", "especie": "species"}


def test_alias_deduplicates_when_col_in_both_sides():
    left = wrap([Row(**{"familia": "Apiaceae"})])
    right = wrap([Row(**{"familia": "Rosaceae"})])
    result = AliasAnalyzer({"familia": "family"}).build_mapping(
        cols(left), cols(right), left.rows, right.rows
    )
    assert result == {"familia": "family"}


@pytest.mark.integration
def test_semantic_analyzer_warns_and_returns_empty_when_model_missing(caplog):
    analyzer = SemanticAnalyzer(language="en")
    left = wrap([Row(**{"family": "Apiaceae"})])
    right = wrap([Row(**{"0": "Apiaceae"})])
    with patch("spacy.load", side_effect=OSError("model not found")):
        with caplog.at_level(logging.WARNING, logger="tablemerge.analyzers"):
            result = analyzer.build_mapping(
                cols(left), cols(right), left.rows, right.rows
            )
    assert result == {}
    assert "en_core_web_md" in caplog.text


@pytest.mark.integration
def test_semantic_analyzer_warns_on_missing_spacy(caplog):
    analyzer = SemanticAnalyzer(language="en")
    left = wrap([Row(**{"family": "Apiaceae"})])
    right = wrap([Row(**{"0": "Apiaceae"})])
    with patch.dict("sys.modules", {"spacy": None}):
        analyzer._nlp = None
        analyzer._load_failed = False
        with caplog.at_level(logging.WARNING, logger="tablemerge.analyzers"):
            result = analyzer.build_mapping(
                cols(left), cols(right), left.rows, right.rows
            )
    assert result == {}


def test_chain_transitivity():
    left = wrap([Row(**{"family": "Apiaceae"}), Row(**{"family": "Rosaceae"})])
    right = wrap([Row(**{"0": "Apiaceae"}), Row(**{"0": "Rosaceae"})])
    from tablemerge.columns_aligner import ColumnAligner

    aligner = ColumnAligner(
        left,
        right,
        analyzers=[JaccardAnalyzer(), AliasAnalyzer({"family": "official_family"})],
    )
    assert aligner.mapping.get("0") == "official_family"
    assert aligner.mapping.get("family") == "official_family"
