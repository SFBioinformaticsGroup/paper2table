from typing import Protocol

from tablevalidate.schema import ColumnValue, Row, TableFragment, ValueWithAgreement
from tablemerge.spacy_utils import load_spacy_model


class FragmentTransformer(Protocol):
    @property
    def settings(self) -> dict: ...

    def transform_fragment(self, fragment: TableFragment) -> TableFragment: ...


class NullFragmentTransformer:
    @property
    def settings(self) -> dict:
        return {}

    def transform_fragment(self, fragment: TableFragment) -> TableFragment:
        return fragment


class FragmentValuesReverser:
    def __init__(self, language: str = "en"):
        self.language = language
        self._nlp = load_spacy_model(language)

    @property
    def settings(self) -> dict:
        return {"language": self.language}

    def _count_known_words(self, text: str) -> int:
        return sum(
            1
            for w in text.split()
            if len(text) > 2 and self._nlp.vocab[w.lower()].has_vector
        )

    def _row_score(self, row: Row) -> int:
        total = 0
        for value in row.get_columns().values():
            if isinstance(value, str):
                total += self._count_known_words(value)
            elif isinstance(value, list):
                total += sum(self._count_known_words(v.value) for v in value)
        return total

    def _fragment_score(self, fragment: TableFragment) -> int:
        return sum(self._row_score(row) for row in fragment.rows)

    def _reverse_cell(self, value: ColumnValue) -> ColumnValue:
        if isinstance(value, str):
            return value[::-1]
        if isinstance(value, list):
            return [
                ValueWithAgreement(
                    value=v.value[::-1], agreement_level=v.agreement_level
                )
                for v in value
            ]
        return value

    def _transform_row(self, row: Row) -> Row:
        return Row(
            **{
                col: self._reverse_cell(value)
                for col, value in row.get_columns().items()
            },
            agreement_level_=row.agreement_level_,
            sources_=row.sources_,
        )

    def transform_fragment(self, fragment: TableFragment) -> TableFragment:
        reversed_fragment = TableFragment(
            rows=[self._transform_row(row) for row in fragment.rows],
            page=fragment.page,
        )
        if self._fragment_score(reversed_fragment) > self._fragment_score(fragment):
            return reversed_fragment
        return fragment
