import argparse
import random
from pathlib import Path

from tablevalidate.schema import Row, TablesFile
from utils.column_schema import ColumnSchema
from utils.read_path import read_path
from utils.table_fragments import load_papers
from paper2table import __version__


def collect_column_values(
    papers: dict[str, TablesFile], schema: ColumnSchema | None
) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    if schema is not None:
        for column_name in schema.column_names():
            values[column_name] = []

    for tablesfile in papers.values():
        for table in tablesfile.tables:
            for fragment in table.get_table_fragments():
                for row in fragment.rows:
                    columns = (
                        row.get_columns() if schema is not None
                        else row.get_semantic_columns()
                    )
                    for column_name, column_value in columns.items():
                        if schema is not None and column_name not in schema:
                            continue
                        text = Row.to_text(column_value).strip()
                        if not text:
                            continue
                        values.setdefault(column_name, []).append(text)
    return values


def sample_examples(
    values: list[str], count: int, max_length: int | None, rng: random.Random
) -> list[str]:
    candidates = values if max_length is None else [v for v in values if len(v) <= max_length]
    if len(candidates) <= count:
        return list(candidates)
    return rng.sample(candidates, count)


def format_report(samples: dict[str, list[str]]) -> str:
    lines = []
    for column_name, examples in samples.items():
        lines.append(f"{column_name}:")
        if not examples:
            lines.append("  (no examples)")
        for example in examples:
            lines.append(f"  - {example}")
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
    return parser.parse_args()


def main():
    args = parse_args()

    schema_str = read_path(args.schema_path, inline=args.schema)
    schema = ColumnSchema.parse(schema_str) if schema_str else None

    papers = load_papers(Path(args.input_dir))
    values = collect_column_values(papers, schema)

    rng = random.Random(args.seed)
    samples = {
        column_name: sample_examples(
            column_values, args.examples_count, args.max_length, rng
        )
        for column_name, column_values in values.items()
    }

    print(format_report(samples))


if __name__ == "__main__":
    main()
