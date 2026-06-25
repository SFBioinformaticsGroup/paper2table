from dataclasses import dataclass
from typing import Dict, Optional

from tablevalidate.schema import TablesFile


@dataclass
class PaperStats:
    tables: int
    fragments: int
    rows: int
    unique_rows: int
    columns: int
    rows_with_agreement: int
    agreement_percentage: Optional[float] = None
    empty_rows_percentage: Optional[float] = None

    def to_dict(self):
        return {
            "tables": self.tables,
            "fragments": self.fragments,
            "rows": self.rows,
            "unique_rows": self.unique_rows,
            "columns": self.columns,
            "rows_with_agreement": self.rows_with_agreement,
            "agreement_percentage": self.agreement_percentage,
            "empty_rows_percentage": self.empty_rows_percentage,
        }


@dataclass
class GlobalStats:
    papers: int
    tables: int
    fragments: int
    rows: int
    unique_rows: int
    rows_with_agreement: int
    papers_stats: Dict[str, PaperStats]
    global_agreement_percentage: Optional[float] = None

    def to_dict(self):
        return {
            "papers": self.papers,
            "tables": self.tables,
            "fragments": self.fragments,
            "rows": self.rows,
            "unique_rows": self.unique_rows,
            "rows_with_agreement": self.rows_with_agreement,
            "global_agreement_percentage": self.global_agreement_percentage,
            "papers_stats": [
                {key: value.to_dict()} for key, value in self.papers_stats.items()
            ],
        }


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

    if stats.rows > 0:
        stats.global_agreement_percentage = stats.rows_with_agreement / stats.rows * 100

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
        sum(1 for row in fragment.rows if row.is_empty())
        for fragment in all_fragments
    )
    unique_columns = {
        col
        for fragment in all_fragments
        for row in fragment.rows
        for col in row.get_columns()
    }

    agreement_percentage = None
    empty_rows_percentage = None
    if rows_count > 0:
        agreement_percentage = rows_with_agreement / rows_count * 100
        empty_rows_percentage = empty_rows_count / rows_count * 100

    return PaperStats(
        tables=tables_count,
        fragments=fragments_count,
        rows=rows_count,
        unique_rows=unique_rows_count,
        columns=len(unique_columns),
        rows_with_agreement=rows_with_agreement,
        agreement_percentage=agreement_percentage,
        empty_rows_percentage=empty_rows_percentage,
    )
