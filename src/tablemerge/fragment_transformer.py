import re
from typing import Protocol

from tablevalidate.schema import ColumnValue, Row, TableFragment, ValueWithAgreement
from tablemerge.merge import is_header_row
from tablemerge.spacy_utils import load_spacy_model


class FragmentTransformer(Protocol):
    @property
    def settings(self) -> dict: ...

    def transform_fragment(self, fragment: TableFragment) -> TableFragment: ...


_TITLE_ROW_RE = re.compile(
    r"^((figure|table|figura|tabla)\s+|fig\.\s*)\d+", re.IGNORECASE
)

_LEADING_NUMBER_RE = re.compile(r"^(\d+)\.\s+")


class FilterTitleRowsTransformer:
    @property
    def settings(self) -> dict:
        return {}

    def transform_fragment(self, fragment: TableFragment) -> TableFragment:
        head = [row for row in fragment.rows[:3] if not self.is_title_row(row)]
        return TableFragment(rows=head + fragment.rows[3:], page=fragment.page)

    def is_title_row(self, row: Row) -> bool:
        non_empty = {
            col: val
            for col, val in row.get_columns().items()
            if not Row.is_empty_value(val)
        }
        if len(non_empty) == 0:
            return False
        if len(non_empty) == 1:
            text = self.extract_text(next(iter(non_empty.values())))
        else:
            text = "".join(self.extract_text(v) for v in non_empty.values())
        return bool(_TITLE_ROW_RE.match(text.strip()))

    def extract_text(self, val: ColumnValue) -> str:
        if isinstance(val, str):
            return val.strip()
        if isinstance(val, list):
            texts = [v.value.strip() for v in val if v.value.strip()]
            return texts[0] if texts else ""
        return ""


class LeadingRowNumberTransformer:
    @property
    def settings(self) -> dict:
        return {"enabled": True}

    def transform_fragment(self, fragment: TableFragment) -> TableFragment:
        column_names = Row.column_names(fragment.rows)
        columns_to_strip = {
            col for col in column_names if self.should_strip_column(col, fragment.rows)
        }
        if not columns_to_strip:
            return fragment
        return TableFragment(
            rows=[self.transform_row(row, columns_to_strip) for row in fragment.rows],
            page=fragment.page,
        )

    def should_strip_column(self, column: str, rows: list[Row]) -> bool:
        samples: list[str] = []
        for row in rows:
            val = row.get_columns().get(column)
            if val is None or Row.is_empty_value(val):
                continue
            text = self.extract_text(val)
            if text:
                samples.append(text)
            if len(samples) == 5:
                break
        if len(samples) < 2:
            return False
        numbers: list[int] = []
        for text in samples:
            match = _LEADING_NUMBER_RE.match(text)
            if not match:
                return False
            numbers.append(int(match.group(1)))
        return all(numbers[i] < numbers[i + 1] for i in range(len(numbers) - 1))

    def extract_text(self, val: ColumnValue) -> str:
        if isinstance(val, str):
            return val.strip()
        if isinstance(val, list):
            texts = [v.value.strip() for v in val if v.value.strip()]
            return texts[0] if texts else ""
        return ""

    def transform_row(self, row: Row, columns_to_strip: set[str]) -> Row:
        new_cols = {
            col: self.strip_leading_number(val) if col in columns_to_strip else val
            for col, val in row.get_columns().items()
        }
        return Row(
            **new_cols,
            agreement_level_=row.agreement_level_,
            sources_=row.sources_,
            row_=row.row_,
        )

    def strip_leading_number(self, val: ColumnValue) -> ColumnValue:
        if isinstance(val, str):
            return _LEADING_NUMBER_RE.sub("", val)
        if isinstance(val, list):
            return [
                ValueWithAgreement(
                    value=_LEADING_NUMBER_RE.sub("", v.value),
                    agreement_level=v.agreement_level,
                )
                for v in val
            ]
        return val


class FilterEmptyRowsTransformer:
    @property
    def settings(self) -> dict:
        return {}

    def transform_fragment(self, fragment: TableFragment) -> TableFragment:
        return TableFragment(
            rows=[row for row in fragment.rows if not row.is_empty()],
            page=fragment.page,
        )


class FilterHeaderRowsTransformer:
    def __init__(self, hints: list[str] = []):
        self.hints = hints

    @property
    def settings(self) -> dict:
        return {"hints": self.hints}

    def transform_fragment(self, fragment: TableFragment) -> TableFragment:
        return TableFragment(
            rows=[row for row in fragment.rows if not is_header_row(row, self.hints)],
            page=fragment.page,
        )

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
            row_=row.row_,
        )

    def transform_fragment(self, fragment: TableFragment) -> TableFragment:
        reversed_fragment = TableFragment(
            rows=[self._transform_row(row) for row in fragment.rows],
            page=fragment.page,
        )
        if self._fragment_score(reversed_fragment) > self._fragment_score(fragment):
            return reversed_fragment
        return fragment
