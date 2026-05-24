import argparse
import json
import sys
from datetime import datetime as dt
from pathlib import Path
from uuid import uuid4

from tablevalidate.schema import TablesFile
from utils.columns_schema import parse_schema, tokenize_schema

from .analyzers import Analyzer, JaccardAnalyzer, AliasAnalyzer, SemanticAnalyzer
from .merge import (
    merge_tablesfiles,
    filter_semantic_columns,
    filter_header_rows,
    MergeError,
    SimpleCountAgreement,
    DistinctReadersAgreement,
)
from .schema import PostProcessor, SchemaPostProcessor, NullPostProcessor


def read_resultset_metadata(resultset_dir: str) -> dict:
    try:
        with open(
            Path(resultset_dir) / "tables.metadata.json", "r", encoding="utf-8"
        ) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def write_merge_metadata(
    resultset_dirs: list[str],
    output_path: Path,
    resultset_metadata: dict[str, dict],
    settings: dict,
):
    sources = []
    for resultset_dir in resultset_dirs:
        meta = resultset_metadata.get(resultset_dir, {})
        source = {"path": resultset_dir}
        if "uuid" in meta:
            source["uuid"] = meta["uuid"]
        if "reader" in meta:
            source["reader"] = meta["reader"]
        sources.append(source)

    merge_metadata = {
        "reader": "tablemerge",
        "uuid": str(uuid4()),
        "datetime": dt.now().isoformat(),
        "settings": settings,
        "sources": sources,
    }

    output_path.mkdir(parents=True, exist_ok=True)
    metadata_out = output_path / "tables.metadata.json"
    with open(metadata_out, "w", encoding="utf-8") as f:
        json.dump(merge_metadata, f, ensure_ascii=False, indent=2)

    print(f"Metadata written to {metadata_out}")
    return merge_metadata


def load_text_or_file(value: str) -> str:
    path = Path(value)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return value


def load_schema(value: str) -> dict:
    return parse_schema(load_text_or_file(value))


def parse_aliases(text: str) -> dict[str, str]:
    aliases = {}
    for part in tokenize_schema(text):
        if ":" in part:
            alias, target = part.split(":", 1)
            aliases[alias] = target
    return aliases


def build_analyzers(
    align_columns: bool,
    threshold: float,
    use_semantic: bool,
    language: str,
    aliases: dict[str, str],
) -> list[Analyzer]:
    result: list[Analyzer] = []
    if align_columns:
        result.append(JaccardAnalyzer(threshold))
    if aliases:
        result.append(AliasAnalyzer(aliases))
    if use_semantic:
        result.append(SemanticAnalyzer(threshold, language))
    return result


def merge_tablesfiles_paths(
    basename,
    resultset_dirs,
    output_path,
    metadata_map: dict[str, dict],
    agreement,
    only_semantic_columns: bool = False,
    remove_header_rows: bool = False,
    pretty: bool = False,
    analyzers: list[Analyzer] = [],
    post_processor: PostProcessor = NullPostProcessor(),
):
    """
    Merge all the TablesFile of the same basename
    in the given resultset directories
    """
    tablesfiles: list[TablesFile] = []
    for resultset_dir in resultset_dirs:
        tables_path = Path(resultset_dir) / basename
        if tables_path.exists():
            with open(tables_path, "r", encoding="utf-8") as f:
                tablesfile = TablesFile.model_validate(json.load(f))
                tablesfile.uuid = metadata_map.get(resultset_dir, {}).get("uuid")
                tablesfiles.append(tablesfile)

    sizes = [len(tablesfile.tables) for tablesfile in tablesfiles]

    if not any(size > 0 for size in sizes):
        print(f"{basename}: MERGE SKIPPED: All tables are empty")
        return

    try:
        merged_tablesfile: TablesFile = merge_tablesfiles(
            tablesfiles,
            agreement=agreement,
            analyzers=analyzers,
        )
        if only_semantic_columns:
            merged_tablesfile = filter_semantic_columns(merged_tablesfile)
        if remove_header_rows:
            merged_tablesfile = filter_header_rows(merged_tablesfile)
        merged_tablesfile = post_processor.postprocess(merged_tablesfile)
        print(
            f"{basename}: MERGED: {len(tablesfiles)} files"
            f" into {len(merged_tablesfile.tables)} tables"
        )
        with open(output_path / basename, "w", encoding="utf-8") as outfile:
            json.dump(
                merged_tablesfile.model_dump(),
                outfile,
                ensure_ascii=False,
                indent=2 if pretty else None,
            )
    except MergeError as e:
        print(f"{basename}: MERGE FAILED:", str(e))


def merge_resultsets(
    resultset_dirs: list[str],
    output_dir: str,
    metadata_only=False,
    agreement_method: str = "simple-count",
    only_semantic_columns: bool = False,
    remove_header_rows: bool = False,
    pretty: bool = False,
    analyzers: list[Analyzer] = [],
    post_processor: PostProcessor = NullPostProcessor(),
):
    output_path = Path(output_dir)
    resultset_metadata = {d: read_resultset_metadata(d) for d in resultset_dirs}

    settings = {
        "agreement_method": agreement_method,
        "only_semantic_columns": only_semantic_columns,
        "remove_header_rows": remove_header_rows,
        "analyzers": {type(a).__name__: a.settings for a in analyzers},
        "post_processor": post_processor.settings,
    }
    write_merge_metadata(resultset_dirs, output_path, resultset_metadata, settings)

    if metadata_only:
        return

    agreement = (
        DistinctReadersAgreement(
            {
                meta["uuid"]: meta["reader"]
                for meta in resultset_metadata.values()
                if "uuid" in meta and "reader" in meta
            }
        )
        if agreement_method == "distinct-readers"
        else SimpleCountAgreement()
    )

    output_path.mkdir(parents=True, exist_ok=True)

    tablesfiles_basenames = set()
    for resultset_dir in resultset_dirs:
        for tablesfile in Path(resultset_dir).glob("*.tables.json"):
            tablesfiles_basenames.add(tablesfile.name)

    for basename in sorted(list(tablesfiles_basenames)):
        merge_tablesfiles_paths(
            basename,
            resultset_dirs,
            output_path,
            resultset_metadata,
            agreement,
            only_semantic_columns=only_semantic_columns,
            remove_header_rows=remove_header_rows,
            pretty=pretty,
            analyzers=analyzers,
            post_processor=post_processor,
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Merge JSON tables from multiple directories."
    )
    parser.add_argument(
        "-o",
        "--output-directory",
        type=str,
        help="Directory to store merged output",
        default=".",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Only generate the tablemerge metadata file, skip merging",
    )
    parser.add_argument(
        "paths", nargs="+", help="Input directories containing .tables.json files"
    )
    parser.add_argument(
        "--agreement-method",
        choices=["simple-count", "distinct-readers"],
        default="simple-count",
        help="How to compute agreement level (default: simple-count)",
    )
    parser.add_argument(
        "--only-semantic-columns",
        action="store_true",
        help="Remove columns whose names are numeric after merging",
    )
    parser.add_argument(
        "--remove-header-rows",
        action="store_true",
        help=(
            "Remove rows whose non-empty values all match their column header after normalization"
        ),
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print merged output files with indentation",
    )
    parser.add_argument(
        "--align-columns",
        action="store_true",
        help="Align numeric column names to semantic ones using value similarity",
    )
    parser.add_argument(
        "--column-alignment-threshold",
        type=float,
        default=0.5,
        help="Minimum similarity threshold for column alignment (default: 0.5)",
    )
    parser.add_argument(
        "--semantic-column-alignment",
        action="store_true",
        help="Add NLP-based semantic alignment after Jaccard alignment",
    )
    parser.add_argument(
        "--semantic-language",
        choices=["en", "es"],
        default="en",
        help="Language for spaCy model used by --semantic-column-alignment (default: en)",
    )
    parser.add_argument(
        "--column-aliases",
        type=str,
        help='Inline alias mappings, e.g. "familia:family especie:species"',
    )
    parser.add_argument(
        "--column-aliases-path",
        type=str,
        help="Path to a file with alias:target mappings (one per line)",
    )
    parser.add_argument(
        "-p",
        "--schema-path",
        type=str,
        help=(
            "Schema with column:type pairs (file path or inline string). "
            "Required by --filter-schema-columns, --order-schema-columns, "
            "and --coerce-schema-column-types."
        ),
    )
    parser.add_argument(
        "--filter-schema-columns",
        action="store_true",
        help=(
            "Drop merged tables whose rows share no column names with the schema. "
            "Requires -p."
        ),
    )
    parser.add_argument(
        "--order-schema-columns",
        action="store_true",
        help=(
            "Reorder output columns so schema columns come first (in schema order), "
            "followed by any remaining columns. Requires -p."
        ),
    )
    parser.add_argument(
        "--coerce-schema-column-types",
        action="store_true",
        help=(
            "Normalize cell string values in schema columns to the declared type. "
            "Requires -p."
        ),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    schema_flags = [
        args.filter_schema_columns,
        args.order_schema_columns,
        args.coerce_schema_column_types,
    ]
    if any(schema_flags) and not args.schema_path:
        print(
            "Error: --filter-schema-columns, --order-schema-columns, and "
            "--coerce-schema-column-types all require -p/--schema-path.",
            file=sys.stderr,
        )
        sys.exit(1)
    if args.schema_path:
        post_processor = SchemaPostProcessor(
            load_schema(args.schema_path),
            filter_columns=args.filter_schema_columns,
            order_columns=args.order_schema_columns,
            coerce_types=args.coerce_schema_column_types,
        )
    else:
        post_processor = NullPostProcessor()

    aliases: dict[str, str] = {}
    if args.column_aliases:
        aliases.update(parse_aliases(args.column_aliases))
    if args.column_aliases_path:
        aliases.update(parse_aliases(load_text_or_file(args.column_aliases_path)))

    analyzers = build_analyzers(
        align_columns=args.align_columns,
        threshold=args.column_alignment_threshold,
        use_semantic=args.semantic_column_alignment,
        language=args.semantic_language,
        aliases=aliases,
    )

    merge_resultsets(
        args.paths,
        args.output_directory,
        metadata_only=args.metadata_only,
        agreement_method=args.agreement_method,
        only_semantic_columns=args.only_semantic_columns,
        remove_header_rows=args.remove_header_rows,
        pretty=args.pretty,
        analyzers=analyzers,
        post_processor=post_processor,
    )


if __name__ == "__main__":
    main()
