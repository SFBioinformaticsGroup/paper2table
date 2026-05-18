import re
from unidecode import unidecode
from tablevalidate.schema import TableFragment, Row, ColumnValue


def extract_column_str_values(column_value: ColumnValue) -> list[str]:
    """Normalize + transliterate a ColumnValue into a flat list of strings."""
    if isinstance(column_value, str):
        return [unidecode(re.sub(r"\s+", " ", column_value.strip()).lower())]
    return [unidecode(re.sub(r"\s+", " ", vwa.value.strip()).lower()) for vwa in column_value]


def column_value_set(rows: list[Row], col: str) -> set[str]:
    """Collect normalized values of column `col` across all rows."""
    result: set[str] = set()
    for row in rows:
        val = row.get_columns().get(col)
        if val is not None:
            result.update(extract_column_str_values(val))
    return result


def jaccard(a: set[str], b: set[str]) -> float:
    """
    Jaccard similarity: |a ∩ b| / |a ∪ b|.
    Returns 0.0 when both sets are empty (no evidence to compare).
    Range: [0.0, 1.0]. 1.0 means identical value sets; 0.0 means no overlap.
    """
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def all_column_names(rows: list[Row]) -> list[str]:
    """Return ordered, deduplicated column names across all rows."""
    return list(dict.fromkeys(c for row in rows for c in row.get_columns()))


def find_column_mapping(
    left: TableFragment,
    right: TableFragment,
    threshold: float = 0.5,
    max_sample: int = 50,
) -> dict[str, str]:
    """
    Detect correspondences between numeric and semantic column names across two
    fragments, using Jaccard similarity on their normalized value sets.

    Returns a dict mapping numeric_col_name -> semantic_col_name. Only activates
    when one fragment has exclusively numeric column names and the other has
    exclusively semantic ones; returns {} otherwise (both numeric, both semantic,
    or mixed).

    Two columns are considered equivalent when their Jaccard index (size of value
    intersection / size of value union, after normalization) is >= threshold.
    Matching is one-to-one: the best-scoring pair is assigned first, then those
    columns are excluded from subsequent pairings (greedy descending order).

    Args:
        left: one of the two fragments to compare.
        right: the other fragment to compare.
        threshold: minimum Jaccard similarity to consider two columns equivalent.
            0.0 maps everything; 1.0 requires identical value sets. Default 0.5
            tolerates up to half of the values being different (e.g. one table
            has extra rows the other doesn't).
        max_sample: number of rows sampled per fragment for efficiency.
    """
    left_rows = left.rows[:max_sample]
    right_rows = right.rows[:max_sample]
    if not left_rows or not right_rows:
        return {}

    left_cols = all_column_names(left_rows)
    right_cols = all_column_names(right_rows)

    left_numeric = [c for c in left_cols if not Row.is_semantic_column(c)]
    right_numeric = [c for c in right_cols if not Row.is_semantic_column(c)]
    left_semantic = [c for c in left_cols if Row.is_semantic_column(c)]
    right_semantic = [c for c in right_cols if Row.is_semantic_column(c)]

    if right_numeric and left_semantic and not left_numeric:
        numeric_cols, numeric_rows = right_numeric, right_rows
        semantic_cols, semantic_rows = left_semantic, left_rows
    elif left_numeric and right_semantic and not right_numeric:
        numeric_cols, numeric_rows = left_numeric, left_rows
        semantic_cols, semantic_rows = right_semantic, right_rows
    else:
        return {}

    num_sets = {c: column_value_set(numeric_rows, c) for c in numeric_cols}
    sem_sets = {c: column_value_set(semantic_rows, c) for c in semantic_cols}

    scores = [
        (jaccard(num_sets[nc], sem_sets[sc]), nc, sc)
        for nc in numeric_cols
        for sc in semantic_cols
        if jaccard(num_sets[nc], sem_sets[sc]) >= threshold
    ]
    scores.sort(key=lambda x: -x[0])

    mapping: dict[str, str] = {}
    used: set[str] = set()
    for _, nc, sc in scores:
        if nc not in mapping and sc not in used:
            mapping[nc] = sc
            used.add(sc)
    return mapping


def rename_row_columns(row: Row, mapping: dict[str, str]) -> Row:
    if not mapping:
        return row
    return Row(
        agreement_level_=row.agreement_level_,
        sources_=row.sources_,
        **{mapping.get(k, k): v for k, v in row.get_columns().items()},
    )


def rename_fragment_columns(fragment: TableFragment, mapping: dict[str, str]) -> TableFragment:
    if not mapping:
        return fragment
    return TableFragment(
        rows=[rename_row_columns(r, mapping) for r in fragment.rows],
        page=fragment.page,
    )
