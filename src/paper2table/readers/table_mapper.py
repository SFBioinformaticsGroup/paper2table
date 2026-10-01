import re
from typing import Optional, Protocol, cast

import pandas as pd

from utils.column_names import normalize_column_name
from Levenshtein import ratio

from ..mapping import ColumnMapping, TableMapping


Row = list[Optional[str]]


class PDFTable(Protocol):
    def to_dataframe(
        self, column_names_hints: list[str], skip_first_row: bool
    ) -> pd.DataFrame: ...


class TableMapper:
    def __init__(self, table_mapping: TableMapping) -> None:
        self._mapping = table_mapping

    def transform(
        self, extracted_tables: list[PDFTable], page_number: int
    ) -> pd.DataFrame:
        if not extracted_tables:
            raise ValueError("No tables were extracted")
        row_mappings = self._mapping.row_mappings
        if row_mappings is not None:
            header_row, data_rows = self._transform_with_row_mappings(
                extracted_tables, row_mappings
            )
        else:
            header_row, data_rows = self._transform_with_header_mode(
                extracted_tables, page_number
            )

        col_groups = self._resolve_column_groups(header_row)
        data_rows = self._merge_column_groups(data_rows, col_groups)
        column_names = [cm.to_column_name for cm in self._mapping.column_mappings]
        df = pd.DataFrame(
            data_rows, columns=pd.Index(column_names) if column_names else None
        )
        return self._normalize(df)

    def _transform_with_header_mode(self, extracted_tables: list[PDFTable], page_number):
        skip_first_row = self._mapping.header_mode == "all_pages" or (
            self._mapping.header_mode == "first_page_only"
            and page_number == self._mapping.first_page
        )
        raw_df = extracted_tables[-1].to_dataframe(
            column_names_hints=[], skip_first_row=skip_first_row
        )
        rows = raw_df.values.tolist()
        rows = self._remove_bibliographic_rows(rows)
        header_row, data_rows = [], rows
        return header_row, data_rows

    def _transform_with_row_mappings(self, extracted_tables: list[PDFTable], row_mappings):
        raw_df = extracted_tables[-1].to_dataframe(
            column_names_hints=[], skip_first_row=False
        )
        rows: list[Row] = raw_df.values.tolist()
        rows = self._remove_bibliographic_rows(rows)
        rows = self._remove_blank_rows(rows)
        rows = self._remove_empty_columns(rows)
        rows = self._skip_to_header(rows)
        header_row, data_rows = self._split_by_row_mappings(rows, row_mappings)
        return header_row, data_rows

    def _remove_blank_rows(self, rows: list[Row]) -> list[Row]:
        return [row for row in rows if not all(self._is_blank(cell) for cell in row)]

    def _skip_to_header(self, rows: list[Row]) -> list[Row]:
        from_names = [
            cm.from_column_name
            for cm in self._mapping.column_mappings
            if cm.from_column_name
        ]
        if not from_names:
            return rows
        for i, row in enumerate(rows):
            for cell in row:
                cell_text = (cell or "").strip()
                if cell_text and any(name == cell_text for name in from_names):
                    return rows[i:]
        return rows

    def _remove_empty_columns(self, rows: list[Row]) -> list[Row]:
        if not rows:
            return rows
        col_count = max(len(row) for row in rows)
        non_empty = [
            col for col in range(col_count)
            if any(not self._is_blank(row[col] if col < len(row) else None) for row in rows)
        ]
        return [[row[col] if col < len(row) else None for col in non_empty] for row in rows]

    def _remove_bibliographic_rows(self, rows: list[Row]) -> list[Row]:
        footer = self._mapping.footer.lower() if self._mapping.footer else None
        page_footer = self._mapping.page_footer.lower() if self._mapping.page_footer else None
        title = self._mapping.title.lower()

        result = []
        for row in rows:
            row_text = "".join(cell for cell in row if cell).lower()
            if footer is not None and ratio(row_text, footer) > 0.8:
                continue
            if page_footer is not None and ratio(row_text, page_footer) > 0.8:
                continue
            if ratio(row_text, title) > 0.8:
                continue
            result.append(row)
        return result

    def _split_by_row_mappings(
        self, rows: list[Row], row_mappings
    ) -> tuple[Row, list[Row]]:
        header_row_idx = row_mappings.header_row
        if row_mappings.first_data_row is not None:
            first_data_idx = row_mappings.first_data_row
        elif header_row_idx is not None:
            first_data_idx = header_row_idx + 1
        else:
            first_data_idx = 0
        header_row: Row = rows[header_row_idx] if header_row_idx is not None else []
        return header_row, rows[first_data_idx:]

    def _resolve_column_groups(
        self, header_row: Row
    ) -> list[tuple[ColumnMapping, list[int]]]:
        """
        Determines which columns should be accumulated and
        treated as a single unit
        """
        groups: list[tuple[ColumnMapping, list[int]]] = []
        next_start = 0
        for cm in self._mapping.column_mappings:
            indices = self._resolve_column_indices(cm, header_row, next_start)
            groups.append((cm, indices))
            next_start = indices[-1] + 1
        return groups

    def _resolve_column_indices(
        self, column_mapping: ColumnMapping, header_row: Row, next_start: int = 0
    ) -> list[int]:
        if column_mapping.from_column_name is None or not header_row:
            return [column_mapping.from_column_number]
        effective_start = max(column_mapping.from_column_number, next_start)
        start = self._find_header_start(header_row, effective_start)
        indices = self._accumulate_header(header_row, start, column_mapping.from_column_name)
        if indices is None:
            return [column_mapping.from_column_number]
        return indices + self._absorb_trailing_empty(header_row, indices[-1] + 1)

    def _find_header_start(self, header_row: Row, from_column_number: int) -> int:
        start = from_column_number
        while start < len(header_row) and self._is_blank(header_row[start]):
            start += 1
        return start

    def _accumulate_header(
        self, header_row: Row, start: int, target: str
    ) -> list[int] | None:
        accumulated = (header_row[start] or "").strip() if start < len(header_row) else ""
        indices = [start]
        if accumulated == target:
            return indices
        for next_idx in range(start + 1, len(header_row)):
            if not target.startswith(accumulated):
                return None
            accumulated += (header_row[next_idx] or "").strip()
            indices.append(next_idx)
            if accumulated == target:
                return indices
        return None

    def _absorb_trailing_empty(self, header_row: Row, from_idx: int) -> list[int]:
        absorbed = []
        idx = from_idx
        while idx < len(header_row) and self._is_blank(header_row[idx]):
            absorbed.append(idx)
            idx += 1
        return absorbed

    def _is_blank(self, value: Optional[str]) -> bool:
        return value is None or (isinstance(value, str) and value.strip() == "")

    def _merge_column_groups(
        self,
        data_rows: list[Row],
        col_groups: list[tuple[ColumnMapping, list[int]]],
    ) -> list[list[Optional[str]]]:
        merged = []
        for row in data_rows:
            new_row: list[Optional[str]] = []
            for _cm, indices in col_groups:
                cells = [
                    row[i]
                    for i in indices
                    if i < len(row) and not self._is_blank(row[i])
                ]
                new_row.append(" ".join(str(c) for c in cells) if cells else None)
            merged.append(new_row)
        return merged

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        df.rename(columns=lambda col: normalize_column_name(str(col)), inplace=True)
        df = cast(
            pd.DataFrame,
            df.apply(
                lambda row: [
                    v.replace("\n", " ") if isinstance(v, str) else v for v in row
                ]
            ),
        )
        return df
