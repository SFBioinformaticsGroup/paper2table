from typing import Iterable, Optional

from tablemerge.agreement import Agreement, SimpleCountAgreement
from tablevalidate.schema import ColumnValue, Row, TableFragment, ValueWithAgreement


def to_values_with_agreement(column_value: ColumnValue) -> list[ValueWithAgreement]:
    if column_value is None:
        return []
    if isinstance(column_value, str):
        return [ValueWithAgreement(value=column_value, agreement_level=1)]
    return column_value


def _merge_columns_without_agreement(left: Row, right: Row):
    return {
        **right.get_columns(),
        **left.get_columns(),
    }


def _merge_columns_with_agreement(left: Row, right: Row):
    column_values: dict[str, dict[str, int]] = {}
    for row in [left, right]:
        for column_name, column_value in row.get_columns().items():
            values = column_values.setdefault(column_name, {})
            for value_with_agreement in to_values_with_agreement(column_value):
                value = value_with_agreement.value
                if value in values:
                    values[value] += value_with_agreement.agreement_level
                else:
                    values[value] = value_with_agreement.agreement_level
    return {
        column_name: [
            ValueWithAgreement(value=column_value, agreement_level=agreement_level)
            for column_value, agreement_level in column_values.items()
        ]
        for column_name, column_values in column_values.items()
    }


def merge_rows(
    left: Row,
    right: Row,
    agreement: Agreement = SimpleCountAgreement(),
    column_agreement: bool = False,
) -> Row:
    """
    Merges already normalized columns
    """
    agreement_level = agreement.calculate_level(left, right)

    if column_agreement:
        columns = _merge_columns_with_agreement(left, right)
    else:
        columns = _merge_columns_without_agreement(left, right)

    left_sources = left.sources_ or []
    right_sources = right.sources_ or []
    sources = list(dict.fromkeys(left_sources + right_sources)) or None

    return Row(
        citation_=None,
        fragment_=None,
        page_=None,
        path_=None,
        agreement_level_=agreement_level,
        sources_=sources,
        row_=left.row_,
        **columns
    )


class TableFragmentBuilder:
    rows: list[Row]
    page: int
    agreement: Agreement
    column_agreement: bool

    def __init__(
        self,
        page: int,
        initial_rows: Iterable[Row],
        initial_uuid: Optional[str],
        agreement: Agreement,
        column_agreement: bool,
    ):
        self.agreement = agreement
        self.column_agreement = column_agreement
        self.page = page

        self.rows = []
        self.row_ = 0
        self._append_initial(initial_rows, initial_uuid)

    def prepare_next_left_rows(self):
        rows = self.rows
        self.rows = []
        self.row_ = 0
        return list(rows)

    def append_from_right(self, rows: list[Row], right_source: Optional[str]):
        self._append_aside(rows, right_source)

    def append_from_left(self, row: Row):
        self._append_aside([row])

    def append_from_both(self, left: Row, right: Row, right_source: Optional[str]):

        self._append(
            # TODO stamping code could be simplified
            merge_rows(
                self._stamp(left, self.row_),
                self._stamp(right, self.row_, right_source),
                agreement=self.agreement,
                column_agreement=self.column_agreement,
            )
        )

        self.row_ += 1

    def build(self):
        return TableFragment(
            rows=[r for r in self.rows if not r.is_empty()],
            page=self.page,
        )

    def _append_initial(self, rows: Iterable[Row], right_source: Optional[str] = None):
        for idx, row in enumerate(rows):
            self._append(self._stamp(row, idx, right_source))

    def _append_aside(self, rows: Iterable[Row], right_source: Optional[str] = None):
        for row in rows:
            self._append(self._stamp(row, self.row_, right_source))
            self.row_ += 1

    def _append(self, row: Row):
        self.rows.append(row)

    def _stamp(self, row: Row, row_: int, source_uuid: Optional[str] = None):
        return row.model_copy(
            update={
                "sources_": [source_uuid] if source_uuid else row.sources_,
                "row_": row_,
            }
        )
