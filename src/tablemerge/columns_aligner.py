from tablevalidate.schema import TableFragment, Row, ColumnValue
from .analyzers import LoadTimeAnalyzer, MergeTimeAnalyzer, REMOVE_COLUMN


def append_column_value(existing: ColumnValue, new_value: ColumnValue) -> ColumnValue:
    if existing is None:
        return new_value
    if new_value is None:
        return existing
    if isinstance(existing, str) and isinstance(new_value, str):
        if not existing:
            return new_value
        if not new_value:
            return existing
        sep = " " if existing.endswith(".") else ". "
        return existing + sep + new_value
    # TODO this is not totally right
    if isinstance(existing, list) and isinstance(new_value, list):
        return existing + new_value
    return existing


class BaseColumnAligner:
    mapping: dict[str, str]

    def __init__(self, max_sample: int = 50):
        self.max_sample = max_sample

    def rename_row(self, row: Row) -> Row:
        if not self.mapping:
            return row
        renamed_columns = {}
        for column, value in row.get_columns().items():
            new_name = self.rename_column(column)
            if new_name != REMOVE_COLUMN:
                if new_name in renamed_columns:
                    if column == new_name:
                        renamed_columns[new_name] = append_column_value(value, renamed_columns[new_name])
                    else:
                        renamed_columns[new_name] = append_column_value(renamed_columns[new_name], value)
                else:
                    renamed_columns[new_name] = value
        return Row(
            agreement_level_=row.agreement_level_,
            sources_=row.sources_,
            row_=row.row_,
            **renamed_columns,
        )

    def rename_column(self, col_name: str) -> str:
        return self.mapping.get(col_name, col_name)

    def sample_rows(self, fragment: TableFragment) -> list:
        return fragment.rows[: self.max_sample]

    def filter_remaining(self, remaining: list[str], mapped: set) -> list[str]:
        return [c for c in remaining if c not in mapped]

    def accumulate_mapping(
        self, accumulated: dict[str, str], new_mapping: dict[str, str]
    ) -> set:
        for k in accumulated:
            if accumulated[k] in new_mapping:
                accumulated[k] = new_mapping[accumulated[k]]
        accumulated.update(new_mapping)
        return set(new_mapping.keys())


class LoadTimeColumnAligner(BaseColumnAligner):
    def __init__(
        self,
        fragment: TableFragment,
        analyzers: list[LoadTimeAnalyzer] = [],
        max_sample: int = 50,
    ):
        super().__init__(max_sample)
        self.analyzers = analyzers
        self.mapping = self.build_mapping(fragment)

    def build_mapping(self, fragment: TableFragment) -> dict[str, str]:
        rows = self.sample_rows(fragment)
        if not rows:
            return {}
        remaining = fragment.get_column_names()
        accumulated: dict[str, str] = {}
        for analyzer in self.analyzers:
            candidates = remaining + list(accumulated.values())
            if not candidates:
                break
            new_mapping = analyzer.build_mapping(candidates, rows)
            if not new_mapping:
                continue
            mapped = self.accumulate_mapping(accumulated, new_mapping)
            remaining = self.filter_remaining(remaining, mapped)
        return accumulated


class MergeTimeColumnAligner(BaseColumnAligner):
    def __init__(
        self,
        left: TableFragment,
        right: TableFragment | None,
        analyzers: list[MergeTimeAnalyzer] = [],
        max_sample: int = 50,
    ):
        super().__init__(max_sample)
        self.analyzers = analyzers
        self.mapping = self.build_mapping(left, right)

    def build_mapping(
        self, left: TableFragment, right: TableFragment | None
    ) -> dict[str, str]:
        left_rows = self.sample_rows(left)
        right_rows = self.sample_rows(right) if right is not None else []
        if not left_rows:
            return {}
        remaining_left = left.get_column_names()
        remaining_right = right.get_column_names() if right is not None else []
        accumulated: dict[str, str] = {}
        for analyzer in self.analyzers:
            if not remaining_left and not remaining_right:
                break
            new_mapping = analyzer.build_mapping(
                remaining_left, remaining_right, left_rows, right_rows
            )
            if not new_mapping:
                continue
            mapped = self.accumulate_mapping(accumulated, new_mapping)
            remaining_left = self.filter_remaining(remaining_left, mapped)
            remaining_right = self.filter_remaining(remaining_right, mapped)
        return accumulated
