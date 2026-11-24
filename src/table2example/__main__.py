import argparse
import random
from pathlib import Path

from utils.column_schema import ColumnSchema
from utils.read_path import read_path
from utils.sample_values import collect_column_values, count_values, sample_values
from utils.table_fragments import load_papers
from paper2table import __version__


def format_report(samples: dict[str, list[str]]) -> str:
    lines = []
    for column_name, examples in samples.items():
        lines.append(f"{column_name}:")
        if not examples:
            lines.append("  (no examples)")
        for example in examples:
            lines.append(f"  - {example}")
    return "\n".join(lines)


def format_value_counts(samples: dict[str, list[tuple[str, int]]]) -> str:
    lines = []
    for column_name, entries in samples.items():
        lines.append(f"{column_name}:")
        if not entries:
            lines.append("  (no examples)")
        for value, occurrences in entries:
            lines.append(f"  - {value} ({occurrences})")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show random example values for each column in a tables directory."
    )
    parser.add_argument(
        "--version", action="version", version=f"table2example {__version__}"
    )
    parser.add_argument(
        "input_dir",
        help="Directory containing .tables.json paper files",
        metavar="PATH",
    )
    parser.add_argument(
        "--schema",
        type=str,
        help="Inline schema with column:type pairs. Restricts output to schema columns.",
    )
    parser.add_argument(
        "-p",
        "--schema-path",
        type=str,
        help="Path to a schema file. Restricts output to schema columns.",
    )
    parser.add_argument(
        "-N",
        "--examples-count",
        type=int,
        default=5,
        help="Number of examples to show per column (default: 5).",
    )
    parser.add_argument(
        "-L",
        "--max-length",
        type=int,
        default=None,
        help="Maximum length (in characters) for an example. Longer values are skipped.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible sampling.",
    )
    parser.add_argument(
        "--value-counts",
        action="store_true",
        help="Show unique values sorted by occurrence count (descending), with counts.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    schema_str = read_path(args.schema_path, inline=args.schema)
    schema = ColumnSchema.parse(schema_str) if schema_str else None

    papers = load_papers(Path(args.input_dir))
    values = collect_column_values(papers, schema)

    if args.value_counts:
        samples = {
            column_name: count_values(
                column_values, args.examples_count, args.max_length
            )
            for column_name, column_values in values.items()
        }
        print(format_value_counts(samples))
    else:
        rng = random.Random(args.seed)
        samples = {
            column_name: sample_values(
                column_values, args.examples_count, args.max_length, rng
            )
            for column_name, column_values in values.items()
        }
        print(format_report(samples))


if __name__ == "__main__":
    main()
