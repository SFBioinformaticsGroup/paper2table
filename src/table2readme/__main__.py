import argparse
import sys
from pathlib import Path

from paper2table import __version__
from utils.cli import add_na_values_args
from utils.read_path import read_path

from .generator import load_column_aliases, write_readme


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate a README.md scaffold describing an extraction project. "
            "Input directories are specified explicitly: any path omitted is not inspected."
        )
    )
    parser.add_argument(
        "--version", action="version", version=f"table2readme {__version__}"
    )
    parser.add_argument(
        "--merges-path",
        type=str,
        help="Directory with tablemerge outputs (*.tables.json); used for the Papers table.",
    )
    parser.add_argument(
        "--tables-path",
        type=str,
        help="Directory with per-run paper2table outputs (<run-id>/tables.metadata.json); used for the Tools section.",
    )
    parser.add_argument(
        "--gathers-path",
        type=str,
        help="Directory with tablegather outputs; used for the Files section.",
    )
    parser.add_argument(
        "--schema",
        type=str,
        help="Inline schema, one 'column:type' per line.",
    )
    parser.add_argument(
        "-p",
        "--schema-path",
        type=str,
        help="Path to a schema file with one 'column:type' per line (same format as --schema).",
    )
    parser.add_argument(
        "--column-aliases",
        type=str,
        help='Inline alias mappings, one "alias:target" per line',
    )
    parser.add_argument(
        "--column-aliases-path",
        type=str,
        help="Path to a file with alias:target mappings (one per line)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="README.md",
        metavar="PATH",
        help="Output README path (default: README.md)",
    )
    parser.add_argument(
        "--override",
        action="store_true",
        help="Overwrite the output file if it already exists",
    )
    add_na_values_args(parser)

    args = parser.parse_args()

    merges_path = Path(args.merges_path) if args.merges_path else None
    tables_path = Path(args.tables_path) if args.tables_path else None
    gathers_path = Path(args.gathers_path) if args.gathers_path else None

    schema_content = read_path(args.schema_path, inline=args.schema)
    aliases = load_column_aliases(args.column_aliases, args.column_aliases_path)
    output_path = Path(args.output)

    wrote = write_readme(
        output_path,
        merges_path,
        tables_path,
        gathers_path,
        schema_content,
        aliases,
        args.override,
    )
    if not wrote:
        print(
            f"[table2readme] {output_path} already exists; use --override to replace",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
