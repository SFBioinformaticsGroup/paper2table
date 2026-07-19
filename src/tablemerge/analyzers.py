import re
from typing import Optional, Protocol

from unidecode import unidecode
import spacy

from tablevalidate.schema import ColumnValue, Row
from tablemerge.spacy_utils import load_spacy_model
from utils.column_names import normalize_column_name
from utils.column_schema import ColumnSchema

REMOVE_COLUMN = "<remove>"


def column_value_to_strings(value: ColumnValue) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [entry.value for entry in value]


def renamable_source_columns(
    columns: list[str], schema: Optional[ColumnSchema]
) -> list[str]:
    """Columns eligible to be renamed. With schema: any column not in schema.
    Without schema: only numeric columns."""
    if schema:
        return [c for c in columns if c not in schema]
    return [c for c in columns if not Row.is_semantic_column(c)]


def renamable_target_columns(
    columns: list[str], schema: Optional[ColumnSchema]
) -> list[str]:
    """Columns eligible as rename targets. With schema: columns in schema.
    Without schema: only semantic columns."""
    if schema:
        return [c for c in columns if c in schema]
    return [c for c in columns if Row.is_semantic_column(c)]


# ====================
# Load Time Analyzers
# ===================


class LoadTimeAnalyzer(Protocol):
    def build_mapping(
        self,
        column_names: list[str],
        rows: list[Row],
    ) -> dict[str, str]: ...


class HintsLoadTimeAnalyzer:
    """Enabled by --hints-column-alignment safe|unsafe. Runs at load time via LoadTimeColumnAligner.

    Inspects the first non-empty row of a fragment. If at least one candidate
    column's value normalizes to a known hint, treats the row as a header row and
    renames ALL candidate columns to their normalized first-row values (including
    columns whose value is not in the hints list). Runs before AliasLoadTimeAnalyzer and
    ColumnNameSemanticLoadTimeAnalyzer.

    safe=True (default): only considers non-semantic columns.
    safe=False: considers all columns, including semantic ones.
    """

    def __init__(self, hints: list[str], safe: bool = True):
        self.hints = hints
        self.safe = safe

    def build_mapping(
        self,
        column_names: list[str],
        rows: list[Row],
    ) -> dict[str, str]:
        if self.safe:
            candidates = [c for c in column_names if not Row.is_semantic_column(c)]
        else:
            candidates = list(column_names)
        if not candidates:
            return {}
        first_row = next((r for r in rows if not r.is_empty()), None)
        if first_row is None:
            return {}
        row_values = self._normalized_values(first_row, candidates)
        hints_set = set(self.hints)
        if not any(val in hints_set for val in row_values.values()):
            return {}
        return row_values

    def _normalized_values(self, row: Row, columns: list[str]) -> dict[str, str]:
        result: dict[str, str] = {}
        for column in columns:
            val = row.get_columns().get(column)
            if val is None:
                continue
            strings = [s.strip() for s in column_value_to_strings(val) if s.strip()]
            if strings:
                result[column] = normalize_column_name(strings[0])
        return result


class AliasLoadTimeAnalyzer:
    """Enabled by --column-aliases / --column-aliases-path. Runs at load time via LoadTimeColumnAligner.

    Applies an explicit user-provided rename dictionary to each fragment independently.
    No heuristics, no data inspection. Makes sense when sources use different column names
    for the same concept (e.g. "familia" → "family"). Works on any column regardless of
    numeric/semantic classification.

    A target value of REMOVE_COLUMN ("<remove>") signals that the column should be dropped
    entirely from the fragment (e.g. "notes:<remove>" removes the "notes" column).
    """

    def __init__(self, aliases: dict[str, str]):
        self.aliases = aliases

    def build_mapping(
        self,
        column_names: list[str],
        rows: list[Row],
    ) -> dict[str, str]:
        all_columns = list(dict.fromkeys(column_names))
        normalized_aliases = {normalize_column_name(k): v for k, v in self.aliases.items()}
        return {
            column: normalized_aliases[normalize_column_name(column)]
            for column in all_columns
            if normalize_column_name(column) in normalized_aliases
        }


class ColumnNameSemanticLoadTimeAnalyzer:
    """Enabled by --semantic-column-alignment. Runs at load time via LoadTimeColumnAligner.

    Renames columns not in the schema to schema column names by computing spaCy word-vector
    similarity between each candidate column's cell values and each schema column name.
    Candidates include numeric columns ("0", "1", ...) and semantic columns whose name is
    not already in the schema. Does nothing without a schema or when all columns are already
    in the schema.
    """

    def __init__(
        self,
        threshold: float = 0.5,
        language: str = "en",
        schema: Optional[ColumnSchema] = None,
    ):
        self.threshold = threshold
        self.language = language
        self.schema = schema
        self._nlp = None

    def build_mapping(
        self,
        column_names: list[str],
        rows: list[Row],
    ) -> dict[str, str]:
        if not self.schema:
            return {}

        candidates = renamable_source_columns(column_names, self.schema)

        if not candidates:
            return {}

        schema_columns = self.schema.column_names()
        nlp = self.load_model()
        scores = []

        for candidate in candidates:
            values = self.sample_values(rows, candidate)
            if not values:
                continue
            column_name_score = (
                self.semantic_score(nlp, values, candidate)
                if Row.is_semantic_column(candidate)
                else None
            )
            for schema_column in schema_columns:
                score = self.semantic_score(nlp, values, schema_column)
                if score < self.threshold:
                    continue
                if column_name_score is not None and column_name_score >= score:
                    continue
                scores.append((score, candidate, schema_column))

        return self._greedy_assignment(scores)

    def _greedy_assignment(
        self, scores: list[tuple[float, str, str]]
    ) -> dict[str, str]:
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

    def sample_values(self, rows: list[Row], column_name: str) -> list[str]:
        values = []
        for row in rows:
            cell = row.get_columns().get(column_name)
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
        self, nlp: spacy.language.Language, values: list[str], column_name: str
    ) -> float:
        column_name_doc = nlp(column_name.replace("_", " ").replace("-", " "))
        if not column_name_doc.has_vector:
            return 0.0
        scores = []
        for value in values:
            value_doc = nlp(value[:128])
            if value_doc.has_vector:
                scores.append(column_name_doc.similarity(value_doc))
        return sum(scores) / len(scores) if scores else 0.0


# ====================
# Merge Time Analyzers
# ====================


class MergeTimeAnalyzer(Protocol):
    def build_mapping(
        self,
        left_column_names: list[str],
        right_column_names: list[str],
        left_rows: list[Row],
        right_rows: list[Row],
    ) -> dict[str, str]: ...


class JaccardMergeTimeAnalyzer:
    """Enabled by --jaccard-column-alignment. Runs at merge time via MergeTimeColumnAligner.

    Renames numeric columns ("0", "1", ...) to semantic ones ("family", "scientific_name", ...)
    by comparing cell values across two fragments using Jaccard similarity.
    Works when fragments share overlapping data, e.g. column "0" and column "family"
    both contain "Apiaceae", "Rosaceae". Requires one side to be all-numeric and the other
    all-semantic; otherwise does nothing.

    When schema is provided, also renames semantic columns that are not in the schema to
    schema columns from the opposing fragment, using the same Jaccard value-overlap logic.
    """

    def __init__(self, threshold: float = 0.5, schema: Optional[ColumnSchema] = None):
        self.threshold = threshold
        self.schema = schema

    def build_mapping(
        self,
        left_column_names: list[str],
        right_column_names: list[str],
        left_rows: list[Row],
        right_rows: list[Row],
    ) -> dict[str, str]:
        left_sources = renamable_source_columns(left_column_names, self.schema)
        right_sources = renamable_source_columns(right_column_names, self.schema)
        left_targets = renamable_target_columns(left_column_names, self.schema)
        right_targets = renamable_target_columns(right_column_names, self.schema)

        if right_sources and left_targets and not left_sources:
            source_columns, source_rows = right_sources, right_rows
            target_column_names, target_rows = left_targets, left_rows
        elif left_sources and right_targets and not right_sources:
            source_columns, source_rows = left_sources, left_rows
            target_column_names, target_rows = right_targets, right_rows
        else:
            return {}

        source_sets = {c: self.column_value_set(source_rows, c) for c in source_columns}
        target_sets = {
            c: self.column_value_set(target_rows, c) for c in target_column_names
        }

        scores = [
            (self.jaccard(source_sets[source], target_sets[target]), source, target)
            for source in source_columns
            for target in target_column_names
            if self.jaccard(source_sets[source], target_sets[target]) >= self.threshold
        ]
        scores.sort(key=lambda x: -x[0])

        mapping: dict[str, str] = {}
        used_targets: set[str] = set()
        for _, source, target in scores:
            if source not in mapping and target not in used_targets:
                mapping[source] = target
                used_targets.add(target)
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

    def column_value_set(self, rows: list[Row], column: str) -> set[str]:
        result: set[str] = set()
        for row in rows:
            val = row.get_columns().get(column)
            if val is not None:
                result.update(self.extract_column_str_values(val))
        return result

    def jaccard(self, a: set[str], b: set[str]) -> float:
        union = len(a | b)
        return len(a & b) / union if union else 0.0


class ColumnValueSemanticMergeTimeAnalyzer:
    """Enabled by --semantic-column-alignment. Runs at merge time via MergeTimeColumnAligner, after JaccardMergeTimeAnalyzer.

    Renames numeric columns ("0", "1", ...) to semantic ones by computing spaCy word-vector
    similarity between each numeric column's cell values and the semantic column names from
    the opposing fragment. Unlike ColumnNameSemanticLoadTimeAnalyzer (which uses a schema), this
    analyzer uses the column names already present in the other fragment as rename targets,
    so it works without a schema. Requires one side to be all-numeric and the other
    all-semantic; otherwise does nothing.

    When schema is provided, also renames semantic columns that are not in the schema to
    schema columns from the opposing fragment, using the same value-similarity logic.
    """

    def __init__(
        self,
        threshold: float = 0.5,
        language: str = "en",
        schema: Optional[ColumnSchema] = None,
    ):
        self.threshold = threshold
        self.language = language
        self.schema = schema
        self._nlp = None

    def build_mapping(
        self,
        left_column_names: list[str],
        right_column_names: list[str],
        left_rows: list[Row],
        right_rows: list[Row],
    ) -> dict[str, str]:
        left_sources = renamable_source_columns(left_column_names, self.schema)
        right_sources = renamable_source_columns(right_column_names, self.schema)
        left_targets = renamable_target_columns(left_column_names, self.schema)
        right_targets = renamable_target_columns(right_column_names, self.schema)

        if right_sources and left_targets and not left_sources:
            source_columns, source_rows = right_sources, right_rows
            target_column_names = left_targets
        elif left_sources and right_targets and not right_sources:
            source_columns, source_rows = left_sources, left_rows
            target_column_names = right_targets
        else:
            return {}

        nlp = self.load_model()
        scores = []
        for source_column in source_columns:
            values = self.sample_values(source_rows, source_column)
            if not values:
                continue
            for target_column in target_column_names:
                score = self.semantic_score(nlp, values, target_column)
                if score >= self.threshold:
                    scores.append((score, source_column, target_column))

        return self.greedy_assignment(scores)

    def greedy_assignment(self, scores: list[tuple[float, str, str]]) -> dict[str, str]:
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

    def sample_values(self, rows: list[Row], column_name: str) -> list[str]:
        values = []
        for row in rows:
            cell = row.get_columns().get(column_name)
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
        self, nlp: spacy.language.Language, values: list[str], column_name: str
    ) -> float:
        column_name_doc = nlp(column_name.replace("_", " ").replace("-", " "))
        if not column_name_doc.has_vector:
            return 0.0
        scores = []
        for value in values:
            value_doc = nlp(value[:128])
            if value_doc.has_vector:
                scores.append(column_name_doc.similarity(value_doc))
        return sum(scores) / len(scores) if scores else 0.0
