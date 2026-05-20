import re
from unidecode import unidecode
from tablevalidate.schema import TableFragment, Row, ColumnValue


class ColumnAligner:
    def __init__(
        self,
        left: TableFragment,
        right: TableFragment | None,
        threshold: float = 0.5,
        max_sample: int = 50,
    ):
        self.threshold = threshold
        self.max_sample = max_sample
        self.mapping = self._build_mapping(left, right) if right is not None else {}

    def rename_row(self, row: Row) -> Row:
        if not self.mapping:
            return row
        return Row(
            agreement_level_=row.agreement_level_,
            sources_=row.sources_,
            **{self._rename(k): v for k, v in row.get_columns().items()},
        )

    def _rename(self, col_name: str) -> str:
        return self.mapping.get(col_name, col_name)

    def _extract_column_str_values(self, column_value: ColumnValue) -> list[str]:
        if isinstance(column_value, str):
            return [unidecode(re.sub(r"\s+", " ", column_value.strip()).lower())]
        return [
            unidecode(re.sub(r"\s+", " ", vwa.value.strip()).lower())
            for vwa in column_value
        ]

    def _column_value_set(self, rows: list[Row], col: str) -> set[str]:
        result: set[str] = set()
        for row in rows:
            val = row.get_columns().get(col)
            if val is not None:
                result.update(self._extract_column_str_values(val))
        return result

    def _jaccard(self, a: set[str], b: set[str]) -> float:
        union = len(a | b)
        return len(a & b) / union if union else 0.0

    def _all_column_names(self, rows: list[Row]) -> list[str]:
        return list(dict.fromkeys(c for row in rows for c in row.get_columns()))

    def _build_mapping(
        self, left: TableFragment, right: TableFragment
    ) -> dict[str, str]:
        """
        Detect correspondences between numeric and semantic column names across two
        fragments, using Jaccard similarity on their normalized value sets.

        Returns a dict mapping numeric_col_name -> semantic_col_name. Only activates
        when one fragment has exclusively numeric column names and the other has
        exclusively semantic ones; returns {} otherwise (both numeric, both semantic,
        or mixed).

        Two columns are considered equivalent when their Jaccard index is >= self.threshold.
        Matching is one-to-one: the best-scoring pair is assigned first, then those
        columns are excluded from subsequent pairings (greedy descending order).
        """
        left_rows = left.rows[: self.max_sample]
        right_rows = right.rows[: self.max_sample]
        if not left_rows or not right_rows:
            return {}

        left_cols = self._all_column_names(left_rows)
        right_cols = self._all_column_names(right_rows)

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

        num_sets = {c: self._column_value_set(numeric_rows, c) for c in numeric_cols}
        sem_sets = {c: self._column_value_set(semantic_rows, c) for c in semantic_cols}

        scores = [
            (self._jaccard(num_sets[nc], sem_sets[sc]), nc, sc)
            for nc in numeric_cols
            for sc in semantic_cols
            if self._jaccard(num_sets[nc], sem_sets[sc]) >= self.threshold
        ]
        scores.sort(key=lambda x: -x[0])

        mapping: dict[str, str] = {}
        used: set[str] = set()
        for _, nc, sc in scores:
            if nc not in mapping and sc not in used:
                mapping[nc] = sc
                used.add(sc)
        return mapping
