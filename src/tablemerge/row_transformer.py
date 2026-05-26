from typing import Protocol

from tablevalidate.schema import ColumnValue, Row, ValueWithAgreement
from tablemerge.spacy_utils import load_spacy_model


class RowTransformer(Protocol):
    @property
    def settings(self) -> dict: ...

    def transform_row(self, row: Row) -> Row: ...


class NullRowTransformer:
    @property
    def settings(self) -> dict:
        return {}

    def transform_row(self, row: Row) -> Row:
        return row


class RowReverser:
    def __init__(self, language: str = "en"):
        self.language = language
        self._nlp = load_spacy_model(language)

    @property
    def settings(self) -> dict:
        return {"language": self.language}

    def count_known_words(self, text: str) -> int:
        return sum(1 for w in text.split() if self._nlp.vocab[w.lower()].has_vector)

    def row_score(self, row: Row) -> int:
        total = 0
        for value in row.get_columns().values():
            if isinstance(value, str):
                total += self.count_known_words(value)
            elif isinstance(value, list):
                total += sum(self.count_known_words(v.value) for v in value)
        return total

    def reverse_cell(self, value: ColumnValue) -> ColumnValue:
        if isinstance(value, str):
            return value[::-1]
        if isinstance(value, list):
            return [
                ValueWithAgreement(value=v.value[::-1], agreement_level=v.agreement_level)
                for v in value
            ]
        return value

    def transform_row(self, row: Row) -> Row:
        reversed_row = Row(
            **{col: self.reverse_cell(value) for col, value in row.get_columns().items()},
            agreement_level_=row.agreement_level_,
            sources_=row.sources_,
        )
        if self.row_score(reversed_row) > self.row_score(row):
            return reversed_row
        return row
