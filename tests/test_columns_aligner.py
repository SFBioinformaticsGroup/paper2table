import pytest

from tablemerge.columns_aligner import find_column_mapping
from tablevalidate.schema import (
    Row,
    TableFragment,
)


def wrap(rows: list[Row]) -> TableFragment:
    return TableFragment(rows=rows, page=1)


def test_find_column_mapping_right_numeric_to_left_semantic():
    # "0" vs "family": {"apiaceae","rosaceae"} ∩ {"apiaceae","rosaceae"} = 2/2 = 1.0
    # "1" vs "scientific_name": same → 1.0
    left = wrap(
        [
            Row(**{"family": "Apiaceae", "scientific_name": "Ammi majus L."}),
            Row(**{"family": "Rosaceae", "scientific_name": "Rosa canina L."}),
        ]
    )
    right = wrap(
        [
            Row(**{"0": "Apiaceae", "1": "Ammi majus L."}),
            Row(**{"0": "Rosaceae", "1": "Rosa canina L."}),
        ]
    )
    assert find_column_mapping(left, right) == {"0": "family", "1": "scientific_name"}


def test_find_column_mapping_left_numeric_to_right_semantic():
    # Symmetric direction: left is numeric, right is semantic
    left = wrap(
        [
            Row(**{"0": "lunes", "1": "monday"}),
            Row(**{"0": "martes", "1": "tuesday"}),
        ]
    )
    right = wrap(
        [
            Row(**{"dia": "lunes", "day": "monday"}),
            Row(**{"dia": "martes", "day": "tuesday"}),
        ]
    )
    assert find_column_mapping(left, right) == {"0": "dia", "1": "day"}


def test_find_column_mapping_both_semantic_returns_empty():
    left = wrap([Row(**{"family": "Apiaceae"})])
    right = wrap([Row(**{"family": "Apiaceae"})])
    assert find_column_mapping(left, right) == {}


def test_find_column_mapping_both_numeric_returns_empty():
    left = wrap([Row(**{"0": "Apiaceae"})])
    right = wrap([Row(**{"0": "Apiaceae"})])
    assert find_column_mapping(left, right) == {}


def test_find_column_mapping_no_value_overlap_returns_empty():
    # "0" vs "family": {"red","blue"} ∩ {"apiaceae","rosaceae"} = 0/4 = 0.0
    # 0.0 < 0.5 (default threshold) → no mapping
    left = wrap(
        [
            Row(**{"family": "Apiaceae"}),
            Row(**{"family": "Rosaceae"}),
        ]
    )
    right = wrap(
        [
            Row(**{"0": "red"}),
            Row(**{"0": "blue"}),
        ]
    )
    assert find_column_mapping(left, right) == {}


def test_find_column_mapping_partial_overlap_above_threshold():
    # "0" vs "family": {"apiaceae"} ∩ {"apiaceae","rosaceae"} = 1/2 = 0.5
    # 0.5 >= 0.5 (default threshold) → matches
    left = wrap(
        [
            Row(**{"family": "Apiaceae"}),
            Row(**{"family": "Rosaceae"}),
        ]
    )
    right = wrap(
        [
            Row(**{"0": "Apiaceae"}),
        ]
    )
    assert find_column_mapping(left, right) == {"0": "family"}


@pytest.mark.parametrize(
    "threshold,expected",
    [
        # Jaccard("0" vs "family") = |{"apiaceae"}| / |{"apiaceae","rosaceae","lamiaceae"}| = 1/3 ≈ 0.33
        (1.0, {}),  # 0.33 < 1.0 → no match
        (0.5, {}),  # 0.33 < 0.5 → no match
        (0.34, {}),  # 0.33 < 0.34 → no match
        (0.33, {"0": "family"}),  # 0.33 >= 0.33 → match
        (0.3, {"0": "family"}),  # 0.33 >= 0.3 → match
        (0.0, {"0": "family"}),  # 0.33 >= 0.0 → match
    ],
)
def test_find_column_mapping_threshold_controls_match(threshold, expected):
    # left "family" has 3 values; right "0" shares only 1 of them → Jaccard = 1/3
    left = wrap(
        [
            Row(**{"family": "Apiaceae"}),
            Row(**{"family": "Rosaceae"}),
            Row(**{"family": "Lamiaceae"}),
        ]
    )
    right = wrap([Row(**{"0": "Apiaceae"})])
    assert find_column_mapping(left, right, threshold=threshold) == expected


@pytest.mark.parametrize(
    "threshold,expected",
    [
        # Jaccard("0" vs "family") = |{"apiaceae"}| / |{"apiaceae","rosaceae"}| = 1/2 = 0.5
        (0.6, {}),  # 0.5 < 0.6 → no match
        (0.5, {"0": "family"}),  # 0.5 >= 0.5 → match (at boundary)
        (0.4, {"0": "family"}),  # 0.5 >= 0.4 → match
    ],
)
def test_find_column_mapping_threshold_boundary(threshold, expected):
    # left "family" has 2 values; right "0" shares exactly 1 → Jaccard = 0.5
    left = wrap(
        [
            Row(**{"family": "Apiaceae"}),
            Row(**{"family": "Rosaceae"}),
        ]
    )
    right = wrap([Row(**{"0": "Apiaceae"})])
    assert find_column_mapping(left, right, threshold=threshold) == expected


def test_find_column_mapping_empty_fragment():
    left = wrap([])
    right = wrap([Row(**{"0": "Apiaceae"})])
    assert find_column_mapping(left, right) == {}


def test_find_column_mapping_one_col_matches_one_does_not():
    # "0" vs "family": {"apiaceae","rosaceae"} → 1.0 → matches
    # "1" vs "scientific_name": {"zzz","www"} ∩ {"ammi majus l.","rosa canina l."} = 0/4 = 0.0 → no match
    left = wrap(
        [
            Row(**{"family": "Apiaceae", "scientific_name": "Ammi majus L."}),
            Row(**{"family": "Rosaceae", "scientific_name": "Rosa canina L."}),
        ]
    )
    right = wrap(
        [
            Row(**{"0": "Apiaceae", "1": "zzz"}),
            Row(**{"0": "Rosaceae", "1": "www"}),
        ]
    )
    assert find_column_mapping(left, right) == {"0": "family"}
