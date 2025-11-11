import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Literal

from .stats import GlobalStats, update_papers_stats


def read_paper(paper_path):
    with open(paper_path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_papers_stats(path: str) -> GlobalStats:
    input_path = Path(path)
    stats = GlobalStats(papers=0, papers_stats={}, rows=0, tables=0)

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
    return parser.parse_args()


def format_stats(stats: GlobalStats) -> str:
    lines = []
    lines.append("Global Stats:")
    lines.append(f"  Papers: {stats.papers}")
    lines.append(f"  Tables: {stats.tables}")
    lines.append(f"  Rows: {stats.rows}")
    lines.append("")
    lines.append("Per-Paper Stats:")
    for paper, paper_stats in stats.papers_stats.items():
        lines.append(f"- {paper}:")
        lines.append(f"    Tables: {paper_stats.tables}")
        lines.append(f"    Rows: {paper_stats.rows}")
        lines.append(f"    Rows with agreement > 1: {paper_stats.rows_with_agreement}")
        if paper_stats.agreement_percentage is not None:
            lines.append(
                f"    Agreement percentage: {paper_stats.agreement_percentage:.2f}%"
            )
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
        print(format_stats(stats))


if __name__ == "__main__":
    main()
