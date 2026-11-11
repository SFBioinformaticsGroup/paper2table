import argparse
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import cast

from utils.column_schema import ColumnSchema
from utils.column_values import (
    DEFAULT_NA_VALUES,
    configure_na_values,
    parse_na_values,
)
from utils.postprocessor import PostProcessor, build_postprocessors


def add_postprocessor_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--schema",
        type=str,
        help=(
            "Inline schema, one 'column:type' per line. "
            "Required by --filter-schema-columns, --order-schema-columns, "
            "and --coerce-schema-column-types."
        ),
    )
    parser.add_argument(
        "-p",
        "--schema-path",
        type=str,
        help="Path to a schema file with one 'column:type' per line (same format as --schema).",
    )
    parser.add_argument(
        "--filter-schema-columns",
        action="store_true",
        help=(
            "Drop tables whose rows share no column names with the schema. "
            "Requires --schema/--schema-path."
        ),
    )
    parser.add_argument(
        "--order-schema-columns",
        action="store_true",
        help=(
            "Reorder output columns so schema columns come first (in schema order), "
            "followed by any remaining columns. Requires --schema/--schema-path."
        ),
    )
    parser.add_argument(
        "--coerce-schema-column-types",
        action="store_true",
        help=(
            "Normalize cell string values in schema columns to the declared type. "
            "Requires --schema/--schema-path."
        ),
    )
    parser.add_argument(
        "--filter-semantic-columns",
        action="store_true",
        help="Remove columns whose names are numeric",
    )
    parser.add_argument(
        "--no-drop-empty-columns",
        action="store_false",
        dest="drop_empty_columns",
        default=True,
        help="Skip dropping columns that are entirely empty",
    )
    parser.add_argument(
        "--no-drop-empty-tables",
        action="store_false",
        dest="drop_empty_tables",
        default=True,
        help="Skip dropping tables that are entirely empty",
    )


class ConfigureNoDataExpressionsAction(argparse.Action):
    """Parse the inline string and reconfigure NA_VALUES at parse time."""

    def __call__(self, parser, namespace, values, option_string=None):
        configure_na_values(parse_na_values(cast(str, values)))
        setattr(namespace, self.dest, values)


class ConfigureNoDataExpressionsPathAction(argparse.Action):
    """Read the file and reconfigure NA_VALUES at parse time."""

    def __call__(self, parser, namespace, values, option_string=None):
        text = Path(cast(str, values)).read_text(encoding="utf-8")
        configure_na_values(parse_na_values(text))
        setattr(namespace, self.dest, values)


def add_na_values_args(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--na-values",
        action=ConfigureNoDataExpressionsAction,
        help=(
            "Newline-separated list of expressions to treat as empty, "
            f"REPLACING the defaults ({",".join(DEFAULT_NA_VALUES)}). "
            "Use --na-values-path for a file."
        ),
    )
    parser.add_argument(
        "--na-values-path",
        action=ConfigureNoDataExpressionsPathAction,
        help=(
            "Path to a file with one na value per line "
            "(same format as --na-values)."
        ),
    )


def build_postprocessors_from_args(
    args, schema: ColumnSchema | None
) -> list[PostProcessor]:
    schema_required = [
        (args.filter_schema_columns, "--filter-schema-columns"),
        (args.order_schema_columns, "--order-schema-columns"),
        (args.coerce_schema_column_types, "--coerce-schema-column-types"),
    ]
    for flag, name in schema_required:
        if flag and schema is None:
            print(f"Error: {name} requires --schema/--schema-path.", file=sys.stderr)
            sys.exit(1)
    return build_postprocessors(
        schema=schema,
        filter_columns=args.filter_schema_columns,
        order_columns=args.order_schema_columns,
        coerce_types=args.coerce_schema_column_types,
        filter_semantic_columns=args.filter_semantic_columns,
        drop_empty_columns=args.drop_empty_columns,
        drop_empty_tables=args.drop_empty_tables,
    )
