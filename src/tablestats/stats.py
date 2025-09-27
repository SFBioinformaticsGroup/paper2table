from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PaperStats:
    tables: int
    rows: int
    rows_with_agreement: int
    agreement_percentage: Optional[float] = None

    def to_dict(self):
        return {
            "tables": self.tables,
            "rows": self.rows,
            "rows_with_agreement": self.rows_with_agreement,
            "agreement_percentage": self.agreement_percentage,
        }


@dataclass
class GlobalStats:
    papers: int
    tables: int
    rows: int
    papers_stats: Dict[str, PaperStats]

    def to_dict(self):
        return {
            "papers": self.papers,
            "tables": self.tables,
            "rows": self.rows,
            "papers_stats": [
                {key: value.to_dict()} for key, value in self.papers_stats.items()
            ],
        }


def update_papers_stats(stats: GlobalStats, paper_filename: str, paper_data: dict):
    paper_stats = compute_paper_stats(paper_data)

    stats.papers += 1
    stats.tables += paper_stats.tables
    stats.rows += paper_stats.rows

    stats.papers_stats[paper_filename] = paper_stats


def compute_paper_stats(paper_data) -> PaperStats:
    tables = paper_data.get("tables", [])
    tables_count = len(tables)
    rows_count = sum(len(t.get("rows", [])) for t in tables)
    rows_with_agreement = sum(
        sum(1 for r in table.get("rows", []) if r.get("$agreement_level", 0) > 1)
        for table in tables
    )

    agreement_percentage = None
    if rows_count > 0:
        agreement_percentage = rows_with_agreement / rows_count * 100

    return PaperStats(
        tables=tables_count,
        rows=rows_count,
        rows_with_agreement=rows_with_agreement,
        agreement_percentage=agreement_percentage,
    )
