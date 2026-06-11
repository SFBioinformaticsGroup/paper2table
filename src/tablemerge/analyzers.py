import re
from typing import Protocol

from unidecode import unidecode
import spacy

from tablevalidate.schema import ColumnValue, Row
from tablemerge.schema import Schema
from tablemerge.spacy_utils import load_spacy_model
from utils.column_names import normalize_column_name


def column_value_to_strings(value: ColumnValue) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [entry.value for entry in value]


class LoadTimeAnalyzer(Protocol):
    @property
    def settings(self) -> dict: ...

    def build_mapping(
        self,
        column_names: list[str],
        rows: list[Row],
    ) -> dict[str, str]: ...


class MergeTimeAnalyzer(Protocol):
    @property
    def settings(self) -> dict: ...

    def build_mapping(
        self,
        left_column_names: list[str],
        right_column_names: list[str],
        left_rows: list[Row],
        right_rows: list[Row],
    ) -> dict[str, str]: ...


class HintsAnalyzer:
    """Enabled by --hints-column-alignment. Runs at load time via LoadTimeColumnAligner.

    Inspects the first non-empty row of a fragment. If at least one non-semantic
    column's value normalizes to a known hint, treats the row as a header row and
    renames ALL non-semantic columns to their normalized first-row values (including
    columns whose value is not in the hints list). Runs before AliasAnalyzer and
    SemanticAnalyzer.
    """

    def __init__(self, hints: list[str]):
        self.hints = hints

    @property
    def settings(self) -> dict:
        return {"hints": self.hints}

    def build_mapping(
        self,
        column_names: list[str],
        rows: list[Row],
    ) -> dict[str, str]:
        non_semantic = [c for c in column_names if not Row.is_semantic_column(c)]
        if not non_semantic:
            return {}
        first_row = next((r for r in rows if not r.is_empty()), None)
        if first_row is None:
            return {}
        row_values = self._non_semantic_normalized_values(first_row, non_semantic)
        hints_set = set(self.hints)
        if not any(val in hints_set for val in row_values.values()):
            return {}
        return row_values

    def _non_semantic_normalized_values(self, row: Row, non_semantic: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        for col in non_semantic:
            val = row.get_columns().get(col)
            if val is None:
                continue
            strings = [s.strip() for s in column_value_to_strings(val) if s.strip()]
            if strings:
                result[col] = normalize_column_name(strings[0])
        return result


class JaccardAnalyzer:
    """Enabled by --jaccard-column-alignment. Runs at merge time via MergeTimeColumnAligner.

    Renames numeric columns ("0", "1", ...) to semantic ones ("family", "scientific_name", ...)
    by comparing cell values across two fragments using Jaccard similarity (intersection over
    union). Works when fragments share overlapping data, e.g. column "0" and column "family"
    both contain "Apiaceae", "Rosaceae". Requires one side to be all-numeric and the other
    all-semantic; otherwise does nothing.
    """

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

    @property
    def settings(self) -> dict:
        return {"threshold": self.threshold}

    def build_mapping(
        self,
        left_column_names: list[str],
        right_column_names: list[str],
        left_rows: list[Row],
        right_rows: list[Row],
    ) -> dict[str, str]:
        left_numeric = [c for c in left_column_names if not Row.is_semantic_column(c)]
        right_numeric = [c for c in right_column_names if not Row.is_semantic_column(c)]
        left_semantic = [c for c in left_column_names if Row.is_semantic_column(c)]
        right_semantic = [c for c in right_column_names if Row.is_semantic_column(c)]

        if right_numeric and left_semantic and not left_numeric:
            numeric_cols, numeric_rows = right_numeric, right_rows
            semantic_cols, semantic_rows = left_semantic, left_rows
        elif left_numeric and right_semantic and not right_numeric:
            numeric_cols, numeric_rows = left_numeric, left_rows
            semantic_cols, semantic_rows = right_semantic, right_rows
        else:
            return {}

        num_sets = {c: self.column_value_set(numeric_rows, c) for c in numeric_cols}
        sem_sets = {c: self.column_value_set(semantic_rows, c) for c in semantic_cols}

        scores = [
            (self.jaccard(num_sets[nc], sem_sets[sc]), nc, sc)
            for nc in numeric_cols
            for sc in semantic_cols
            if self.jaccard(num_sets[nc], sem_sets[sc]) >= self.threshold
        ]
        scores.sort(key=lambda x: -x[0])

        mapping: dict[str, str] = {}
        used: set[str] = set()
        for _, nc, sc in scores:
            if nc not in mapping and sc not in used:
                mapping[nc] = sc
                used.add(sc)
        return mapping

    def extract_column_str_values(self, column_value: ColumnValue) -> list[str]:
        if column_value is None:
            return []
        if isinstance(column_value, str):
            return [unidecode(re.sub(r"\s+", " ", column_value.strip()).lower())]
        return [
            unidecode(re.sub(r"\s+", " ", entry.value.strip()).lower())
            for entry in column_value
        ]

    def column_value_set(self, rows: list[Row], col: str) -> set[str]:
        result: set[str] = set()
        for row in rows:
            val = row.get_columns().get(col)
            if val is not None:
                result.update(self.extract_column_str_values(val))
        return result

    def jaccard(self, a: set[str], b: set[str]) -> float:
        union = len(a | b)
        return len(a & b) / union if union else 0.0


class AliasAnalyzer:
    """Enabled by --column-aliases / --column-aliases-path. Runs at load time via LoadTimeColumnAligner.

    Applies an explicit user-provided rename dictionary to each fragment independently.
    No heuristics, no data inspection. Makes sense when sources use different column names
    for the same concept (e.g. "familia" → "family"). Works on any column regardless of
    numeric/semantic classification.
    """

    def __init__(self, aliases: dict[str, str]):
        self.aliases = aliases

    @property
    def settings(self) -> dict:
        return {"aliases": self.aliases}

    def build_mapping(
        self,
        column_names: list[str],
        rows: list[Row],
    ) -> dict[str, str]:
        all_cols = list(dict.fromkeys(column_names))
        return {col: self.aliases[col] for col in all_cols if col in self.aliases}


class SemanticAnalyzer:
    """Enabled by --semantic-column-alignment. Runs at load time via LoadTimeColumnAligner.

    Renames numeric columns ("0", "1", ...) in a fragment to schema column names by computing
    spaCy word-vector similarity between each numeric column's cell values and each schema
    column name. Does nothing without a schema or when no numeric columns are present.
    """

    def __init__(self, threshold: float = 0.5, language: str = "en", schema: Schema = {}):
        self.threshold = threshold
        self.language = language
        self.schema = schema
        self._nlp = None

    @property
    def settings(self) -> dict:
        return {"threshold": self.threshold, "language": self.language}

    def build_mapping(
        self,
        column_names: list[str],
        rows: list[Row],
    ) -> dict[str, str]:
        if not self.schema:
            return {}

        numeric = [c for c in column_names if not Row.is_semantic_column(c)]

        if not numeric:
            return {}

        schema_cols = list(self.schema.keys())
        nlp = self.load_model()
        scores = []

        for numeric_col in numeric:
            values = self.sample_values(rows, numeric_col)
            if not values:
                continue
            for schema_col in schema_cols:
                score = self.semantic_score(nlp, values, schema_col)
                if score >= self.threshold:
                    scores.append((score, numeric_col, schema_col))

        return self._greedy_assignment(scores)

    def _greedy_assignment(self, scores: list[tuple[float, str, str]]) -> dict[str, str]:
        """Resolves (score, source, target) candidates into a 1-to-1 mapping.

        When one source matches multiple targets, the highest-scoring target wins.
        When multiple sources match the same target, the highest-scoring source wins.
        """
        sorted_scores = sorted(scores, key=lambda x: -x[0])
        mapping: dict[str, str] = {}
        used_targets: set[str] = set()
        for _, source, target in sorted_scores:
            if source not in mapping and target not in used_targets:
                mapping[source] = target
                used_targets.add(target)
        return mapping

    def load_model(self):
        if self._nlp is None:
            self._nlp = load_spacy_model(self.language)
        return self._nlp

    def sample_values(self, rows: list[Row], col_name: str) -> list[str]:
        values = []
        for row in rows:
            cell = row.get_columns().get(col_name)
            if cell is None:
                continue
            text = (
                cell.strip()
                if isinstance(cell, str)
                else (cell[0].value.strip() if cell else "")
            )
            if text:
                values.append(text)
        return values

    def semantic_score(
        self, nlp: spacy.language.Language, values: list[str], col_name: str
    ) -> float:
        col_name_doc = nlp(col_name.replace("_", " ").replace("-", " "))
        if not col_name_doc.has_vector:
            return 0.0
        scores = []
        for value in values:
            value_doc = nlp(value[:128])
            if value_doc.has_vector:
                scores.append(col_name_doc.similarity(value_doc))
        return sum(scores) / len(scores) if scores else 0.0
