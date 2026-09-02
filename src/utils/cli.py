import sys
from utils.column_schema import ColumnSchema
from utils.postprocessor import PostProcessor, build_postprocessors


def add_postprocessor_args(parser) -> None:
    parser.add_argument(
        "--schema",
        type=str,
        help=(
            "Inline schema with column:type pairs. "
            "Required by --filter-schema-columns, --order-schema-columns, "
            "and --coerce-schema-column-types."
        ),
    )
    parser.add_argument(
        "-p",
        "--schema-path",
        type=str,
        help="Path to a schema file with column:type pairs (same format as --schema).",
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
