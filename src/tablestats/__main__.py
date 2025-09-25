import argparse
import json
from pathlib import Path
from .stats import compute_paper_stats
from collections import OrderedDict



def read_paper(paper_path):
    with open(paper_path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_papers_stats(input_dir):
    input_path = Path(input_dir)

    stats = {
        "papers": 0,
        "tables": 0,
        "rows": 0,
        "papers_stats": {},
    }

    for paper_file in input_path.glob("*.tables.json"):
        paper_data = read_paper(paper_file)
        paper_stats = compute_paper_stats(paper_data)

        stats["papers"] += 1
        stats["tables"] += paper_stats["tables"]
        stats["rows"] += paper_stats["rows"]

        stats["papers_stats"][paper_file.name] = paper_stats

    stats["papers_stats"] = stats["papers_stats"]

    return stats


def save_stats(stats, output_file):
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Compute stats for JSON tables directory."
    )
    parser.add_argument(
        "input_dir",
        help="Directory containing tables.metadata.json and .tables.json paper files",
    )
    parser.add_argument("--out", help="Optional output JSON file for stats")
    return parser.parse_args()

def format_report(stats):
    lines = []
    lines.append("Global Stats:")
    lines.append(f"  Papers: {stats['papers']}")
    lines.append(f"  Tables: {stats['tables']}")
    lines.append(f"  Rows: {stats['rows']}")
    lines.append("")
    lines.append("Per-Paper Stats:")
    for paper, paper_stats in stats["papers_stats"].items():
        lines.append(f"- {paper}:")
        lines.append(f"    Tables: {paper_stats['tables']}")
        lines.append(f"    Rows: {paper_stats['rows']}")
        lines.append(f"    Rows with agreement > 1: {paper_stats['rows_with_agreement']}")
        if "agreement_percentage" in paper_stats:
            lines.append(f"    Agreement percentage: {paper_stats['agreement_percentage']:.2f}%")
    return "\n".join(lines)



def main():
    args = parse_arguments()
    stats = compute_papers_stats(args.input_dir)

    if args.out:
        save_stats(stats, args.out)
    else:
        print(format_report(stats))


if __name__ == "__main__":
    main()
