import logging
import re
from typing import Protocol

from unidecode import unidecode

from tablevalidate.schema import ColumnValue, Row

logger = logging.getLogger(__name__)

SPACY_MODELS = {
    "en": "en_core_web_md",
    "es": "es_core_news_md",
}


class Analyzer(Protocol):
    def build_mapping(
        self,
        left_column_names: list[str],
        right_column_names: list[str],
        left_rows: list[Row],
        right_rows: list[Row],
    ) -> dict[str, str]: ...


class JaccardAnalyzer:
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold

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
        if isinstance(column_value, str):
            return [unidecode(re.sub(r"\s+", " ", column_value.strip()).lower())]
        return [
            unidecode(re.sub(r"\s+", " ", vwa.value.strip()).lower())
            for vwa in column_value
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
    def __init__(self, aliases: dict[str, str]):
        self.aliases = aliases

    def build_mapping(
        self,
        left_column_names: list[str],
        right_column_names: list[str],
        left_rows: list[Row],
        right_rows: list[Row],
    ) -> dict[str, str]:
        all_cols = list(dict.fromkeys(left_column_names + right_column_names))
        return {col: self.aliases[col] for col in all_cols if col in self.aliases}


class SemanticAnalyzer:
    def __init__(self, threshold: float = 0.5, language: str = "en"):
        self.threshold = threshold
        self.language = language
        self._nlp = None
        self._load_failed = False

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
            semantic_cols = left_semantic
        elif left_numeric and right_semantic and not right_numeric:
            numeric_cols, numeric_rows = left_numeric, left_rows
            semantic_cols = right_semantic
        else:
            return {}

        nlp = self.load_model()
        if nlp is None:
            return {}

        scores = []
        for nc in numeric_cols:
            values = self.sample_values(numeric_rows, nc)
            if not values:
                continue
            for sc in semantic_cols:
                score = self.semantic_score(nlp, values, sc)
                if score >= self.threshold:
                    scores.append((score, nc, sc))

        scores.sort(key=lambda x: -x[0])
        mapping: dict[str, str] = {}
        used: set[str] = set()
        for _, nc, sc in scores:
            if nc not in mapping and sc not in used:
                mapping[nc] = sc
                used.add(sc)
        return mapping

    def load_model(self):
        if self._load_failed:
            return None
        if self._nlp is not None:
            return self._nlp
        model = SPACY_MODELS.get(self.language, f"{self.language}_core_web_md")
        try:
            import spacy

            self._nlp = spacy.load(model)
        except ImportError:
            logger.warning("spaCy is not installed. Run: pip install spacy")
            self._load_failed = True
            return None
        except OSError:
            logger.warning(
                "spaCy model %r not found. Run: python -m spacy download %s",
                model,
                model,
            )
            self._load_failed = True
            return None
        return self._nlp

    def sample_values(self, rows: list[Row], col: str) -> list[str]:
        values = []
        for row in rows:
            val = row.get_columns().get(col)
            if val is None:
                continue
            s = (
                val.strip()
                if isinstance(val, str)
                else (val[0].value.strip() if val else "")
            )
            if s:
                values.append(s)
        return values

    def semantic_score(self, nlp, values: list[str], col_name: str) -> float:
        col_doc = nlp(col_name.replace("_", " "))
        if not col_doc.has_vector:
            return 0.0
        scores = []
        for val in values:
            val_doc = nlp(val)
            if val_doc.has_vector:
                scores.append(col_doc.similarity(val_doc))
        return sum(scores) / len(scores) if scores else 0.0
