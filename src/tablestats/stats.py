from dataclasses import dataclass
from typing import Dict, List, Optional

from tablevalidate.schema import Row, TablesFile


@dataclass
class PaperStats:
    tables: int
    fragments: int
    rows: int
    unique_rows: int
    columns: int
    rows_with_agreement: int
    rows_in_shared_groups: int
    rows_with_shared_values: int
    agreement_percentage: Optional[float] = None
    empty_rows_percentage: Optional[float] = None
    shared_values_percentage: Optional[float] = None

    def to_dict(self):
        return {
            "tables": self.tables,
            "fragments": self.fragments,
            "rows": self.rows,
            "unique_rows": self.unique_rows,
            "columns": self.columns,
            "rows_with_agreement": self.rows_with_agreement,
            "rows_in_shared_groups": self.rows_in_shared_groups,
            "rows_with_shared_values": self.rows_with_shared_values,
            "agreement_percentage": self.agreement_percentage,
            "empty_rows_percentage": self.empty_rows_percentage,
            "shared_values_percentage": self.shared_values_percentage,
        }


@dataclass
class GlobalStats:
    papers: int
    tables: int
    fragments: int
    rows: int
    unique_rows: int
    rows_with_agreement: int
    rows_in_shared_groups: int
    rows_with_shared_values: int
    papers_stats: Dict[str, PaperStats]
    global_agreement_percentage: Optional[float] = None
    global_shared_values_percentage: Optional[float] = None

    def to_dict(self):
        return {
            "papers": self.papers,
            "tables": self.tables,
            "fragments": self.fragments,
            "rows": self.rows,
            "unique_rows": self.unique_rows,
            "rows_with_agreement": self.rows_with_agreement,
            "rows_in_shared_groups": self.rows_in_shared_groups,
            "rows_with_shared_values": self.rows_with_shared_values,
            "global_agreement_percentage": self.global_agreement_percentage,
            "global_shared_values_percentage": self.global_shared_values_percentage,
            "papers_stats": [
                {key: value.to_dict()} for key, value in self.papers_stats.items()
            ],
        }


def row_value_strings(row: Row) -> frozenset:
    result = set()
    for col, value in row.get_columns().items():
        if value is None:
            continue
        if isinstance(value, str):
            normalized = value.strip()
            if normalized:
                result.add((col, normalized))
        else:
            for v in value:
                normalized = v.value.strip()
                if normalized:
                    result.add((col, normalized))
    return frozenset(result)


def count_shared_values(tables: list) -> tuple:
    rows_in_groups = 0
    rows_with_shared_values = 0

    for table in tables:
        all_rows = [
            row
            for fragment in table.get_table_fragments()
            for row in fragment.rows
            if row.row_ is not None
        ]

        groups: Dict[int, List[Row]] = {}
        for row in all_rows:
            groups.setdefault(row.row_, []).append(row)

        for group in groups.values():
            if len(group) < 2:
                continue
            rows_in_groups += len(group)
            value_sets = [row_value_strings(row) for row in group]
            for i, vset in enumerate(value_sets):
                if any(vset & value_sets[j] for j in range(len(value_sets)) if j != i):
                    rows_with_shared_values += 1

    return rows_in_groups, rows_with_shared_values


def update_papers_stats(
    stats: GlobalStats, paper_filename: str, paper_data: TablesFile
) -> None:
    paper_stats = compute_paper_stats(paper_data)

    stats.papers += 1
    stats.tables += paper_stats.tables
    stats.fragments += paper_stats.fragments
    stats.rows += paper_stats.rows
    stats.unique_rows += paper_stats.unique_rows
    stats.rows_with_agreement += paper_stats.rows_with_agreement
    stats.rows_in_shared_groups += paper_stats.rows_in_shared_groups
    stats.rows_with_shared_values += paper_stats.rows_with_shared_values

    if stats.rows > 0:
        stats.global_agreement_percentage = stats.rows_with_agreement / stats.rows * 100
    if stats.rows_in_shared_groups > 0:
        stats.global_shared_values_percentage = (
            stats.rows_with_shared_values / stats.rows_in_shared_groups * 100
        )

    stats.papers_stats[paper_filename] = paper_stats


def compute_paper_stats(paper_data: TablesFile) -> PaperStats:
    tables = paper_data.tables
    all_fragments = [
        fragment for table in tables for fragment in table.get_table_fragments()
    ]
    tables_count = len(tables)
    fragments_count = len(all_fragments)
    rows_count = sum(len(fragment.rows) for fragment in all_fragments)
    unique_rows_count = sum(
        len(
            {
                row.row_
                for fragment in table.get_table_fragments()
                for row in fragment.rows
                if row.row_ is not None
            }
        )
        for table in tables
    )
    rows_with_agreement = sum(
        sum(1 for row in fragment.rows if (row.agreement_level_ or 0) > 1)
        for fragment in all_fragments
    )
    empty_rows_count = sum(
        sum(1 for row in fragment.rows if row.is_empty()) for fragment in all_fragments
    )
    unique_columns = {
        col
        for fragment in all_fragments
        for row in fragment.rows
        for col in row.get_columns()
    }
    rows_in_shared_groups, rows_with_shared_values = count_shared_values(tables)

    agreement_percentage = None
    empty_rows_percentage = None
    shared_values_percentage = None
    if rows_count > 0:
        agreement_percentage = rows_with_agreement / rows_count * 100
        empty_rows_percentage = empty_rows_count / rows_count * 100
    if rows_in_shared_groups > 0:
        shared_values_percentage = rows_with_shared_values / rows_in_shared_groups * 100

    return PaperStats(
        tables=tables_count,
        fragments=fragments_count,
        rows=rows_count,
        unique_rows=unique_rows_count,
        columns=len(unique_columns),
        rows_with_agreement=rows_with_agreement,
        rows_in_shared_groups=rows_in_shared_groups,
        rows_with_shared_values=rows_with_shared_values,
        agreement_percentage=agreement_percentage,
        empty_rows_percentage=empty_rows_percentage,
        shared_values_percentage=shared_values_percentage,
    )
