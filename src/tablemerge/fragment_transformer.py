import re
import unicodedata
from typing import Protocol

from tablevalidate.schema import ColumnValue, Row, ScalarValue, TableFragment, ValueWithAgreement
from utils.filters import is_header_row
from tablemerge.spacy_utils import load_spacy_model


class FragmentTransformer(Protocol):
    def transform_fragment(self, fragment: TableFragment) -> TableFragment: ...


_TITLE_ROW_RE = re.compile(
    r"^((figure|table|figura|tabla)\s+|fig\.\s*)\d+", re.IGNORECASE
)

_LEADING_NUMBER_RE = re.compile(r"^(\d+)\.\s+")
# normalize_str also does this, so this is a bit redundant
# but keeping it here for consistency
_DASH_VARIANTS_RE = re.compile(r"[‐‑‒–—―−]")
_GUILLEMETS_RE = re.compile(r"[«»‹›]")
_TYPOGRAPHIC_DOUBLE_QUOTES_RE = re.compile(r"[“”]")
_TYPOGRAPHIC_SINGLE_QUOTES_RE = re.compile(r"[‘’´`ʹʻʼʽ′‵]")
_VOWEL_ACUTE_RE = re.compile(r"([aeiouAEIOU])´")


def _combine_vowel_acute(match: re.Match) -> str:
    combined = unicodedata.normalize("NFC", match.group(1) + "́")
    if len(combined) == 1:
        return combined
    return match.group(0)


_ELLIPSIS_RE = re.compile("…")
_TRAILING_DOT_RE = re.compile(r"^(.*\S{5,})\.$")


class FilterTitleRowsTransformer:

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
            text = Row.to_text(next(iter(non_empty.values())))
        else:
            text = "".join(Row.to_text(v).strip() for v in non_empty.values())
        return bool(_TITLE_ROW_RE.match(text.strip()))


class LeadingRowNumberTransformer:

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
            text = Row.to_text(val).strip()
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

    def transform_row(self, row: Row, columns_to_strip: set[str]) -> Row:
        return row.clone(
            columns={
                col: self.strip_leading_number(val) if col in columns_to_strip else val
                for col, val in row.get_columns().items()
            },
        )

    def strip_leading_number(self, val: ColumnValue) -> ColumnValue:
        return Row.map_text(val, lambda v: _LEADING_NUMBER_RE.sub("", v))


class FilterEmptyRowsTransformer:

    def transform_fragment(self, fragment: TableFragment) -> TableFragment:
        return TableFragment(
            rows=[row for row in fragment.rows if not row.is_empty()],
            page=fragment.page,
        )


class NormalizePunctuationTransformer:

    def transform_fragment(self, fragment: TableFragment) -> TableFragment:
        return TableFragment(
            rows=[self.transform_row(row) for row in fragment.rows],
            page=fragment.page,
        )

    def transform_row(self, row: Row) -> Row:
        return row.clone(
            columns={
                col: self.transform_value(val) for col, val in row.get_columns().items()
            }
        )

    def transform_value(self, val: ColumnValue) -> ColumnValue:
        return Row.map_text(val, self.normalize)

    def normalize(self, text: str) -> str:
        text = _DASH_VARIANTS_RE.sub("-", text)
        text = _GUILLEMETS_RE.sub("", text)
        text = _TYPOGRAPHIC_DOUBLE_QUOTES_RE.sub('"', text)
        text = text.replace('"', "'")
        text = _VOWEL_ACUTE_RE.sub(_combine_vowel_acute, text)
        text = _TYPOGRAPHIC_SINGLE_QUOTES_RE.sub("'", text)
        match = _TRAILING_DOT_RE.match(text)
        if match:
            text = match.group(1)
        text = _ELLIPSIS_RE.sub("...", text)
        return text


class FilterHeaderRowsTransformer:
    def __init__(self, hints: list[str] = []):
        self.hints = hints

    def transform_fragment(self, fragment: TableFragment) -> TableFragment:
        return TableFragment(
            rows=[row for row in fragment.rows if not is_header_row(row, self.hints)],
            page=fragment.page,
        )


class SplitColumnTransformer:
    CONJUNCTIONS: dict[str, set[str]] = {
        "en": {"and", "or"},
        "es": {"y", "e", "o"},
    }

    def __init__(self, language: str = "en") -> None:
        self.language = language
        self._nlp = None

    def load_model(self):
        if self._nlp is None:
            self._nlp = load_spacy_model(self.language)
        return self._nlp

    def find_conjunction_split(self, column_name: str) -> tuple[str, str] | None:
        tokens = column_name.split("_")
        conjunctions = self.CONJUNCTIONS.get(self.language, set())
        for i in range(len(tokens)):
            if tokens[i].lower() in conjunctions and i > 0 and i < len(tokens) - 1:
                return ("_".join(tokens[:i]), "_".join(tokens[i + 1 :]))
        return None

    def normalize_split_part(self, text: str) -> str:
        text = text.strip(" -")
        if text.startswith("(") and text.endswith(")"):
            text = text[1:-1].strip()
        return text

    def split_cell_value(
        self, value: ScalarValue, left_header_doc, right_header_doc
    ) -> tuple[ScalarValue, ScalarValue]:
        if not isinstance(value, str):
            return (value, value)
        tokens = value.split()
        if len(tokens) <= 1:
            return (value, "")
        nlp = self.load_model()
        best_score = -1.0
        best_index = 1
        for i in range(1, len(tokens)):
            left_doc = nlp(" ".join(tokens[:i]))
            right_doc = nlp(" ".join(tokens[i:]))
            score = left_header_doc.similarity(left_doc) + right_header_doc.similarity(
                right_doc
            )
            if score > best_score:
                best_score = score
                best_index = i
        left = self.normalize_split_part(" ".join(tokens[:best_index]))
        right = self.normalize_split_part(" ".join(tokens[best_index:]))
        return (left, right)

    def split_column_value(
        self, column_value: ColumnValue, left_header_doc, right_header_doc
    ) -> tuple[ColumnValue, ColumnValue]:
        if column_value is None:
            return (None, None)
        if isinstance(column_value, str):
            return self.split_cell_value(
                column_value, left_header_doc, right_header_doc
            )
        if not isinstance(column_value, list):
            return (column_value, column_value)
        left_list = []
        right_list = []
        for entry in column_value:
            left_val, right_val = self.split_cell_value(
                entry.value, left_header_doc, right_header_doc
            )
            left_list.append(
                ValueWithAgreement(
                    value=left_val, agreement_level=entry.agreement_level
                )
            )
            right_list.append(
                ValueWithAgreement(
                    value=right_val, agreement_level=entry.agreement_level
                )
            )
        return (left_list, right_list)

    def transform_row(
        self,
        row: Row,
        column_splits: dict[str, tuple[str, str]],
        header_docs: dict[str, tuple],
    ) -> Row:
        new_cols: dict[str, ColumnValue] = {}
        for col, value in row.get_columns().items():
            if col in column_splits:
                left_header, right_header = column_splits[col]
                left_doc, right_doc = header_docs[col]
                left_value, right_value = self.split_column_value(
                    value, left_doc, right_doc
                )
                new_cols[left_header] = left_value
                new_cols[right_header] = right_value
            else:
                new_cols[col] = value
        return row.clone(
            columns=new_cols,
        )

    def transform_fragment(self, fragment: TableFragment) -> TableFragment:
        column_names = Row.column_names(fragment.rows)
        column_splits: dict[str, tuple[str, str]] = {}
        for column_name in column_names:
            result = self.find_conjunction_split(column_name)
            if result is not None:
                column_splits[column_name] = result
        if not column_splits:
            return fragment
        nlp = self.load_model()
        header_docs: dict[str, tuple] = {}
        for col, (left_header, right_header) in column_splits.items():
            header_docs[col] = (
                nlp(left_header.replace("_", " ")),
                nlp(right_header.replace("_", " ")),
            )
        return TableFragment(
            rows=[
                self.transform_row(row, column_splits, header_docs)
                for row in fragment.rows
            ],
            page=fragment.page,
        )


class FragmentValuesReverser:
    def __init__(self, language: str = "en"):
        self.language = language
        self._nlp = load_spacy_model(language)

    def _count_known_words(self, text: str) -> int:
        return sum(
            1
            for w in text.split()
            if len(text) > 2 and self._nlp.vocab[w.lower()].has_vector
        )

    def _row_score(self, row: Row) -> int:
        return sum(
            self._count_known_words(text)
            for value in row.get_column_values()
            for text in Row.to_texts(value)
        )

    def _fragment_score(self, fragment: TableFragment) -> int:
        return sum(self._row_score(row) for row in fragment.rows)

    def _reverse_cell(self, value: ColumnValue) -> ColumnValue:
        return Row.map_text(value, lambda v: v[::-1])

    def _transform_row(self, row: Row) -> Row:
        return row.clone(
            columns={
                col: self._reverse_cell(value)
                for col, value in row.get_columns().items()
            },
        )

    def transform_fragment(self, fragment: TableFragment) -> TableFragment:
        reversed_fragment = TableFragment(
            rows=[self._transform_row(row) for row in fragment.rows],
            page=fragment.page,
        )
        if self._fragment_score(reversed_fragment) > self._fragment_score(fragment):
            return reversed_fragment
        return fragment
