from tablevalidate.schema import TableFragment, Row
from .analyzers import Analyzer


class ColumnAligner:
    def __init__(
        self,
        left: TableFragment,
        right: TableFragment | None,
        analyzers: list[Analyzer],
        max_sample: int = 50,
    ):
        self.analyzers = analyzers
        self.max_sample = max_sample
        self.mapping = self._build_mapping(left, right) if right is not None else {}

    def rename_row(self, row: Row) -> Row:
        if not self.mapping:
            return row
        return Row(
            agreement_level_=row.agreement_level_,
            sources_=row.sources_,
            **{self.rename_column(k): v for k, v in row.get_columns().items()},
        )

    def rename_column(self, col_name: str) -> str:
        return self.mapping.get(col_name, col_name)

    def _build_mapping(
        self, left: TableFragment, right: TableFragment
    ) -> dict[str, str]:
        left_rows = left.rows[: self.max_sample]
        right_rows = right.rows[: self.max_sample]
        if not left_rows or not right_rows:
            return {}

        remaining_left = left.get_column_names()
        remaining_right = right.get_column_names()
        accumulated: dict[str, str] = {}

        for analyzer in self.analyzers:
            if not remaining_left and not remaining_right:
                break
            new_mapping = analyzer.build_mapping(
                remaining_left, remaining_right, left_rows, right_rows
            )
            if not new_mapping:
                continue
            for k in accumulated:
                if accumulated[k] in new_mapping:
                    accumulated[k] = new_mapping[accumulated[k]]
            accumulated.update(new_mapping)
            mapped = set(new_mapping.keys())
            remaining_left = [c for c in remaining_left if c not in mapped]
            remaining_right = [c for c in remaining_right if c not in mapped]

        return accumulated
