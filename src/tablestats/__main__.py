import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Literal

from tablevalidate.schema import ColumnValue, TablesFile
from .stats import GlobalStats, update_papers_stats


def read_paper(paper_path: Path) -> TablesFile:
    with open(paper_path, "r", encoding="utf-8") as f:
        return TablesFile.model_validate(json.load(f))


def compute_papers_stats(path: str) -> GlobalStats:
    input_path = Path(path)
    stats = GlobalStats(papers=0, tables=0, fragments=0, rows=0, unique_rows=0, rows_with_agreement=0, papers_stats={})

    for paper_file in input_path.glob("*.tables.json"):
        paper_data = read_paper(paper_file)
        update_papers_stats(stats, paper_file.name, paper_data)

    return stats


def sort_stats(
    stats: GlobalStats, mode: Literal["none"] | Literal["asc"] | Literal["desc"]
):
    if mode == "none":
        return

    multiplier = 1 if mode == "asc" else -1
    stats.papers_stats = OrderedDict(
        sorted(stats.papers_stats.items(), key=lambda item: multiplier * item[1].tables)
    )


def write_stats(stats: GlobalStats, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(stats.to_dict(), f, ensure_ascii=False)


def infer_type(value: ColumnValue) -> str:
    raw = value if isinstance(value, str) else (value[0].value if value else "")
    stripped = raw.strip()
    if stripped.lower() in ("true", "false"):
        return "bool"
    try:
        int(stripped)
        return "int"
    except ValueError:
        pass
    try:
        float(stripped)
        return "float"
    except ValueError:
        pass
    return "str"


def collect_unique_columns(path: str) -> dict[str, str]:
    input_path = Path(path)
    columns: dict[str, str] = {}
    for paper_file in input_path.glob("*.tables.json"):
        paper_data = read_paper(paper_file)
        for table in paper_data.tables:
            for fragment in table.get_table_fragments():
                if not fragment.rows:
                    continue
                first_row = fragment.rows[0]
                for col_name, col_value in first_row.get_semantic_columns().items():
                    if col_name not in columns:
                        columns[col_name] = infer_type(col_value)
                break
    return columns


def parse_args():
    parser = argparse.ArgumentParser(
        description="Compute stats for JSON tables directory."
    )
    parser.add_argument(
        "path",
        help="Directory containing tables.metadata.json and .tables.json paper files",
        metavar="PATH",
    )
    parser.add_argument("-o", "--out", help="Optional output JSON file for stats")
    parser.add_argument(
        "-s",
        "--sort",
        choices=["none", "asc", "desc"],
        help="Sort by number of tables",
        default="none",
    )
    parser.add_argument(
        "-e",
        "--empty",
        action="store_true",
        help="Only output the names of the empty files. Can't be used with --out",
    )
    parser.add_argument(
        "-C",
        "--columns",
        action="store_true",
        help="Append unique column names and inferred types to the report",
    )
    return parser.parse_args()


def format_stats(stats: GlobalStats, columns: dict[str, str] | None = None) -> str:
    lines = []
    lines.append("Global Stats:")
    lines.append(f"  Papers: {stats.papers}")
    lines.append(f"  Tables: {stats.tables}")
    lines.append(f"  Fragments: {stats.fragments}")
    lines.append(f"  Rows: {stats.rows}")
    lines.append(f"  Unique rows: {stats.unique_rows}")
    lines.append(f"  Rows with agreement > 1: {stats.rows_with_agreement}")
    if stats.global_agreement_percentage is not None:
        lines.append(f"  Global agreement percentage: {stats.global_agreement_percentage:.2f}%")
    lines.append("")
    lines.append("Per-Paper Stats:")
    for paper, paper_stats in stats.papers_stats.items():
        lines.append(f"- {paper}:")
        lines.append(f"    Tables: {paper_stats.tables}")
        lines.append(f"    Fragments: {paper_stats.fragments}")
        lines.append(f"    Rows: {paper_stats.rows}")
        lines.append(f"    Unique rows: {paper_stats.unique_rows}")
        lines.append(f"    Columns: {paper_stats.columns}")
        lines.append(f"    Rows with agreement > 1: {paper_stats.rows_with_agreement}")
        if paper_stats.agreement_percentage is not None:
            lines.append(
                f"    Agreement percentage: {paper_stats.agreement_percentage:.2f}%"
            )
        if paper_stats.empty_rows_percentage is not None:
            lines.append(
                f"    Empty rows percentage: {paper_stats.empty_rows_percentage:.2f}%"
            )
    if columns is not None:
        lines.append("")
        lines.append("Unique Columns:")
        for col_name, col_type in sorted(columns.items()):
            lines.append(f"{col_name}:{col_type}")
    return "\n".join(lines)


def main():
    args = parse_args()
    stats = compute_papers_stats(args.path)
    sort_stats(stats, args.sort)

    if args.empty:
        if args.out:
            print("--empty can't be used with --out")
            sys.exit(1)
        print(
            *[
                path.replace(".tables.json", ".pdf")
                for path, stats in stats.papers_stats.items()
                if not stats.tables
            ]
        )
    elif args.out:
        write_stats(stats, args.out)
    else:
        columns = collect_unique_columns(args.path) if args.columns else None
        print(format_stats(stats, columns))


if __name__ == "__main__":
    main()
