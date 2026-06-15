from tablemerge.agreement import Agreement, SimpleCountAgreement
from tablevalidate.schema import ColumnValue, Row, TableFragment, ValueWithAgreement


def to_values_with_agreement(column_value: ColumnValue) -> list[ValueWithAgreement]:
    if column_value is None:
        return []
    if isinstance(column_value, str):
        return [ValueWithAgreement(value=column_value, agreement_level=1)]
    return column_value


def merge_columns_without_agreement(left: Row, right: Row):
    return {
        **right.normalize().get_columns(),
        **left.normalize().get_columns(),
    }


def merge_columns_with_agreement(left: Row, right: Row):
    column_values: dict[str, dict[str, int]] = {}
    for row in [left, right]:
        for column_name, column_value in row.normalize().get_columns().items():
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
    agreement_level = agreement.calculate_level(left, right)

    if column_agreement:
        columns = merge_columns_with_agreement(left, right)
    else:
        columns = merge_columns_without_agreement(left, right)

    left_sources = left.sources_ or []
    right_sources = right.sources_ or []
    sources = list(dict.fromkeys(left_sources + right_sources)) or None

    return Row(
        agreement_level_=agreement_level, sources_=sources, row_=left.row_, **columns
    )


class TableFragmentBuilder:
    rows: list[Row]
    page: int
    agreement: Agreement
    column_agreement: bool

    def __init__(
        self,
        initial_fragment: TableFragment,
        initial_uuid: str | None,
        agreement: Agreement,
        column_agreement: bool,
    ):
        self.agreement = agreement
        self.column_agreement = column_agreement
        self.page = initial_fragment.page
        do_agreement = agreement is not None
        self.rows = [
            row.model_copy(
                update={"sources_": [initial_uuid] if initial_uuid else None, "row_": i}
            )
            for i, row in enumerate(
                map(lambda r: r.normalize(do_agreement), initial_fragment.rows)
            )
        ]

    def next_left_rows(self):
        rows = self.rows
        self.rows = []
        return list(rows)

    def append_skipped(self, rows: list[Row], source_uuid: str | None):
        for skipped_row in rows:
            stamped = skipped_row.model_copy(
                update={"sources_": [source_uuid] if source_uuid else None}
            )
            self._append(stamped)

    def append_unmatched(self, row: Row):
        self._append(row)

    def merge_and_append(self, left: Row, right: Row):
        self._append(
            merge_rows(
                left,
                right,
                agreement=self.agreement,
                column_agreement=self.column_agreement,
            )
        )

    def build(self):
        return TableFragment(
            rows=[r for r in self.rows if not r.is_empty()], page=self.page
        )

    def _append(self, row: Row):
        self.rows.append(row.normalize(self.agreement is not None))
