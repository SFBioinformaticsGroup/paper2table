import argparse
import functools
import json
import re
import sys
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime as dt
from pathlib import Path
from uuid import uuid4

from tablevalidate.schema import TablesFile
from utils.handle_sigint import handle_sigint
from utils.tokenize_schema import tokenize_schema
from utils.column_names import normalize_column_name
from utils.column_schema import ColumnSchema

handle_sigint()

from .aliases import PaperAlias, parse_column_aliases, parse_paper_aliases
from .settings import MergeSettings, write_settings_file
from .analyzers import (
    LoadTimeAnalyzer,
    MergeTimeAnalyzer,
    HintsLoadTimeAnalyzer,
    JaccardMergeTimeAnalyzer,
    AliasLoadTimeAnalyzer,
    ColumnNameSemanticLoadTimeAnalyzer,
    ColumnValueSemanticMergeTimeAnalyzer,
)
from .agreement import SimpleCountAgreement, DistinctReadersAgreement
from .errors import MergeError
from .tablesfile_loader import TablesFileLoader
from .tablesfile_merger import TablesFileMerger
from .postprocessor import PostProcessor, build_postprocessors
from .fragment_transformer import (
    FragmentTransformer,
    FilterEmptyRowsTransformer,
    FilterHeaderRowsTransformer,
    FilterTitleRowsTransformer,
    FragmentValuesReverser,
    LeadingRowNumberTransformer,
    NormalizePunctuationTransformer,
    SplitColumnTransformer,
)
from .tablesfile_transformer import (
    TablesfileTransformer,
    NullTablesfileTransformer,
    FragmentsExploder,
    SafeConsecutiveFragmentsCompactor,
    UnsafeConsecutiveFragmentsCompactor,
)

TRANSFORMER_MAP = {
    "explode": FragmentsExploder(),
    "safe-compact": SafeConsecutiveFragmentsCompactor(),
    "unsafe-compact": UnsafeConsecutiveFragmentsCompactor(),
}


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
    export_settings: bool = False,
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
    if export_settings:
        write_settings_file(settings, output_path)
    return merge_metadata


def load_text_or_file(value: str) -> str:
    path = Path(value)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return value



def build_analyzers(
    use_jaccard: bool,
    threshold: float,
    use_column_name_semantic: bool,
    use_column_value_semantic: bool,
    language: str,
    aliases: dict[str, str],
    schema: Optional[ColumnSchema] = None,
    hints: list[str] = [],
    hints_mode: str | None = None,
) -> tuple[list[LoadTimeAnalyzer], list[MergeTimeAnalyzer]]:
    load_time: list[LoadTimeAnalyzer] = []
    merge_time: list[MergeTimeAnalyzer] = []

    if hints_mode and hints:
        load_time.append(HintsLoadTimeAnalyzer(hints, safe=(hints_mode == "safe")))
    if aliases:
        load_time.append(AliasLoadTimeAnalyzer(aliases))
    if use_column_name_semantic:
        load_time.append(
            ColumnNameSemanticLoadTimeAnalyzer(threshold, language, schema)
        )

    if use_jaccard:
        merge_time.append(JaccardMergeTimeAnalyzer(threshold, schema))
    if use_column_value_semantic:
        merge_time.append(
            ColumnValueSemanticMergeTimeAnalyzer(threshold, language, schema)
        )

    return load_time, merge_time


TablesFileSource = tuple[str, str, int]  # (resultset_dir, actual_basename, page_offset)


def group_tablesfiles(
    resultset_dirs: list[str],
    paper_aliases: dict[str, PaperAlias],
) -> dict[str, list[TablesFileSource]]:
    groups: dict[str, list[TablesFileSource]] = {}
    for resultset_dir in resultset_dirs:
        for tablesfile in Path(resultset_dir).glob("*.tables.json"):
            actual = tablesfile.name
            stem = actual.removesuffix(".tables.json")
            alias = paper_aliases.get(stem)
            canonical = (alias.canonical if alias else stem) + ".tables.json"
            offset = alias.offset if alias else 0
            groups.setdefault(canonical, []).append((resultset_dir, actual, offset))
    return groups


def filter_groups_by_paper(
    groups: dict[str, list[TablesFileSource]],
    paper_filter: str,
) -> dict[str, list[TablesFileSource]]:
    pattern = paper_filter.removesuffix(".tables.json")
    return {
        k: v
        for k, v in groups.items()
        if re.fullmatch(pattern, k.removesuffix(".tables.json"))
    }


def merge_tablesfiles_paths(
    canonical_basename: str,
    sources: list[TablesFileSource],
    output_path,
    metadata_map: dict[str, dict],
    agreement,
    pretty: bool = False,
    pretransformers: list[FragmentTransformer] = [],
    posttransformers: list[FragmentTransformer] = [],
    load_analyzers: list[LoadTimeAnalyzer] = [],
    merge_analyzers: list[MergeTimeAnalyzer] = [],
    postprocessors: list[PostProcessor] = [],
    tablesfile_transformer: TablesfileTransformer = NullTablesfileTransformer(),
):
    loader = TablesFileLoader(
        pretransformers=pretransformers,
        tablesfile_transformer=tablesfile_transformer,
        analyzers=load_analyzers,
        posttransformers=posttransformers,
    )
    tablesfiles: list[TablesFile] = []
    page_offsets: list[int] = []
    for resultset_dir, actual_basename, page_offset in sources:
        tables_path = Path(resultset_dir) / actual_basename
        if tables_path.exists():
            tablesfile = loader.load(tables_path)
            tablesfile.uuid = metadata_map.get(resultset_dir, {}).get("uuid")
            tablesfiles.append(tablesfile)
            page_offsets.append(page_offset)

    sizes = [len(tablesfile.tables) for tablesfile in tablesfiles]

    if not any(size > 0 for size in sizes):
        print(f"{canonical_basename}: MERGE SKIPPED: All tables are empty")
        return

    try:
        merged_tablesfile: TablesFile = TablesFileMerger(
            agreement=agreement,
            analyzers=merge_analyzers,
        ).merge(tablesfiles, page_offsets=page_offsets)
        for postprocessor in postprocessors:
            merged_tablesfile = postprocessor.postprocess(merged_tablesfile)
        print(
            f"{canonical_basename}: MERGED: {len(tablesfiles)} files"
            f" into {len(merged_tablesfile.tables)} tables"
        )
        with open(output_path / canonical_basename, "w", encoding="utf-8") as outfile:
            json.dump(
                merged_tablesfile.model_dump(),
                outfile,
                ensure_ascii=False,
                indent=2 if pretty else None,
            )
    except MergeError as e:
        print(f"{canonical_basename}: MERGE FAILED:", str(e))


def merge_resultsets(
    resultset_dirs: list[str],
    output_dir: str,
    metadata_only=False,
    agreement_method: str = "simple-count",
    drop_empty_columns: bool = True,
    drop_empty_tables: bool = True,
    only_semantic_columns: bool = False,
    remove_header_rows: bool = False,
    hints: list[str] = [],
    pretty: bool = False,
    pretransformers: list[FragmentTransformer] = [],
    load_analyzers: list[LoadTimeAnalyzer] = [],
    merge_analyzers: list[MergeTimeAnalyzer] = [],
    schema: Optional[ColumnSchema] = None,
    postprocessors: list[PostProcessor] = [],
    tablesfile_transformer: TablesfileTransformer = NullTablesfileTransformer(),
    workers: int = 1,
    paper_aliases: dict[str, PaperAlias] = {},
    paper_filter: str | None = None,
    export_settings: bool = False,
):
    output_path = Path(output_dir)
    resultset_metadata = {d: read_resultset_metadata(d) for d in resultset_dirs}

    posttransformers: list[FragmentTransformer] = []
    if remove_header_rows:
        posttransformers.append(FilterHeaderRowsTransformer(hints))

    settings = {
        "agreement_method": agreement_method,
        "pretransformers": {type(t).__name__: t.settings for t in pretransformers},
        "tablesfile_transformer": tablesfile_transformer.settings,
        "drop_empty_columns": drop_empty_columns,
        "drop_empty_tables": drop_empty_tables,
        "only_semantic_columns": only_semantic_columns,
        "remove_header_rows": remove_header_rows,
        "column_names_hints": hints,
        "schema": schema.serialize() if schema else {},
        "analyzers": {
            **{type(a).__name__: a.settings for a in load_analyzers},
            **{type(a).__name__: a.settings for a in merge_analyzers},
        },
        "postprocessors": {type(p).__name__: p.settings for p in postprocessors},
        "paper_aliases": {
            k: {"canonical": v.canonical, "offset": v.offset}
            for k, v in paper_aliases.items()
        },
    }
    write_merge_metadata(
        resultset_dirs,
        output_path,
        resultset_metadata,
        settings,
        export_settings=export_settings,
    )

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

    groups = group_tablesfiles(resultset_dirs, paper_aliases)
    if paper_filter is not None:
        groups = filter_groups_by_paper(groups, paper_filter)
    sorted_items = sorted(groups.items())
    canonical_basenames = [item[0] for item in sorted_items]
    sources_list = [item[1] for item in sorted_items]

    worker_fn = functools.partial(
        merge_tablesfiles_paths,
        output_path=output_path,
        metadata_map=resultset_metadata,
        agreement=agreement,
        pretransformers=pretransformers,
        posttransformers=posttransformers,
        pretty=pretty,
        load_analyzers=load_analyzers,
        merge_analyzers=merge_analyzers,
        postprocessors=postprocessors,
        tablesfile_transformer=tablesfile_transformer,
    )
    with ThreadPoolExecutor(max_workers=workers) as executor:
        list(executor.map(worker_fn, canonical_basenames, sources_list))


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
        "--no-filter-title-rows",
        action="store_false",
        dest="filter_title_rows",
        default=True,
        help="Skip removing rows whose values match their column names (title rows)",
    )
    parser.add_argument(
        "--no-drop-empty-columns",
        action="store_false",
        dest="drop_empty_columns",
        default=True,
        help="Skip dropping columns that are entirely empty after merging",
    )
    parser.add_argument(
        "--no-drop-empty-tables",
        action="store_false",
        dest="drop_empty_tables",
        default=True,
        help="Skip dropping tables that are entirely empty after merging",
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
        "--jaccard-column-alignment",
        action="store_true",
        help="Align numeric column names to semantic ones using Jaccard value similarity",
    )
    parser.add_argument(
        "--column-alignment-threshold",
        type=float,
        default=0.5,
        help="Minimum similarity threshold for column alignment (default: 0.5)",
    )
    parser.add_argument(
        "--column-name-semantic-alignment",
        action="store_true",
        help=(
            "Rename numeric columns by comparing their cell values against schema column names "
            "using spaCy similarity. Runs at load time. Requires -schema/--schema-path."
        ),
    )
    parser.add_argument(
        "--column-value-semantic-alignment",
        action="store_true",
        help=(
            "Rename numeric columns by comparing their cell values against semantic column names "
            "from the opposing fragment using spaCy similarity. Runs at merge time after Jaccard."
        ),
    )
    parser.add_argument(
        "--semantic-language",
        choices=["en", "es"],
        default="en",
        help=(
            "Language for the spaCy model used by --column-name-semantic-alignment and "
            "--column-value-semantic-alignment (default: en)"
        ),
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
        "--column-names-hints",
        type=str,
        help="Inline column name hints, e.g. 'species family color'",
    )
    parser.add_argument(
        "--column-names-hints-path",
        type=str,
        help="Path to a file with column name hints (one per line, # comments allowed)",
    )
    parser.add_argument(
        "--hints-column-alignment",
        choices=["safe", "unsafe"],
        default=None,
        help=(
            "Rename columns by matching the first row's values against hints. "
            "'safe' renames only non-semantic columns; 'unsafe' also renames semantic columns. "
            "Requires --column-names-hints or --column-names-hints-path."
        ),
    )
    parser.add_argument(
        "--paper-aliases",
        type=str,
        help=(
            'Inline basename alias mappings, e.g. "paper_v1:paper". '
            'Optional third part sets a page offset: "x:y:3" means page N in x '
            "corresponds to page N+3 in y."
        ),
    )
    parser.add_argument(
        "--paper-aliases-path",
        type=str,
        help="Path to a file with alias:target[:offset] basename mappings (one per line)",
    )
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
            "Drop merged tables whose rows share no column names with the schema. "
            "Requires -schema/--schema-path."
        ),
    )
    parser.add_argument(
        "--order-schema-columns",
        action="store_true",
        help=(
            "Reorder output columns so schema columns come first (in schema order), "
            "followed by any remaining columns. Requires -schema/--schema-path."
        ),
    )
    parser.add_argument(
        "--coerce-schema-column-types",
        action="store_true",
        help=(
            "Normalize cell string values in schema columns to the declared type. "
            "Requires -schema/--schema-path."
        ),
    )
    parser.add_argument(
        "--fix-reversed-column-values",
        action="store_true",
        help=(
            "Detect and correct character-reversed cell values using spaCy vocabulary lookup. "
            "Uses --semantic-language for the model."
        ),
    )
    parser.add_argument(
        "--strip-leading-row-numbers",
        action="store_true",
        default=False,
        help=(
            "Strip leading sequential numbering from cell values "
            "('1. text' becomes 'text'). "
            "Applied per column when all sampled values share the pattern and numbers are strictly increasing."
        ),
    )
    parser.add_argument(
        "--normalize-punctuation",
        action="store_true",
        help=(
            "Normalize punctuation in cell values: converts dash variants (en-dash, em-dash) "
            "to hyphens, removes guillemets (« »), converts typographic and double quotes to "
            "single quotes, normalizes apostrophes, converts ellipsis (…) to three dots, "
            "and removes trailing sentence dots when the last word is long."
        ),
    )
    parser.add_argument(
        "--split-conjunction-columns",
        action="store_true",
        help=(
            "Split semantic columns whose names contain a conjunction (e.g. 'city_and_country') "
            "into two columns by finding the best split point in each cell using spaCy similarity. "
            "Uses --semantic-language for the model."
        ),
    )
    parser.add_argument(
        "--transform-tablesfile",
        choices=["explode", "safe-compact", "unsafe-compact"],
        default=None,
        help=(
            "Apply a structural transformation to each loaded tablesfile before merging. "
            "'explode' splits multi-fragment tables into separate single-fragment tables; "
            "'safe-compact' merges consecutive single-fragment tables that share semantic column "
            "names and appear on the same or adjacent pages; "
            "'unsafe-compact' also merges when column count matches regardless of name type or page."
        ),
    )
    parser.add_argument(
        "--paper",
        type=str,
        help="Only merge files matching this paper basename or regexp (e.g. foo, foo.*, bar|baz)",
    )
    parser.add_argument(
        "-j",
        "--workers",
        type=int,
        default=1,
        help="Number of parallel worker threads for merging (default: 1)",
    )
    parser.add_argument(
        "--settings",
        action="store_true",
        help=(
            "Load settings.tablemerge.json from the output directory as defaults. "
            "Explicit CLI flags take precedence."
        ),
    )
    parser.add_argument(
        "--export-settings",
        action="store_true",
        help="Write settings.tablemerge.json to the output directory",
    )

    settings_dict = parse_settings()
    if settings_dict:
        parser.set_defaults(**MergeSettings.from_dict(settings_dict).to_argparse_defaults())

    return parser.parse_args()


def parse_settings():
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--settings", action="store_true")
    pre_parser.add_argument("-o", "--output-directory", default=".")
    pre_args, _ = pre_parser.parse_known_args()
    if pre_args.settings:
        settings_path = Path(pre_args.output_directory) / "settings.tablemerge.json"
        with open(settings_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def main():
    args = parse_args()
    schema_required = [
        (args.filter_schema_columns, "--filter-schema-columns"),
        (args.order_schema_columns, "--order-schema-columns"),
        (args.coerce_schema_column_types, "--coerce-schema-column-types"),
        (args.column_name_semantic_alignment, "--column-name-semantic-alignment"),
    ]
    for flag, name in schema_required:
        if flag and not args.schema_path and not args.schema:
            print(f"Error: {name} requires -schema/--schema-path.", file=sys.stderr)
            sys.exit(1)
    schema: Optional[ColumnSchema] = None
    if args.schema_path:
        with open(args.schema_path, encoding="utf-8") as f:
            schema = ColumnSchema.parse(f.read())
    if args.schema:
        schema = ColumnSchema.parse(args.schema)
    postprocessors = build_postprocessors(
        schema=schema,
        filter_columns=args.filter_schema_columns,
        order_columns=args.order_schema_columns,
        coerce_types=args.coerce_schema_column_types,
        only_semantic_columns=args.only_semantic_columns,
        drop_empty_columns=args.drop_empty_columns,
        drop_empty_tables=args.drop_empty_tables,
    )

    aliases: dict[str, str] = {}
    if args.column_aliases:
        aliases.update(parse_column_aliases(args.column_aliases))
    if args.column_aliases_path:
        aliases.update(
            parse_column_aliases(load_text_or_file(args.column_aliases_path))
        )

    hints: list[str] = []
    if args.column_names_hints:
        hints.extend(
            normalize_column_name(h) for h in tokenize_schema(args.column_names_hints)
        )
    if args.column_names_hints_path:
        hints.extend(
            normalize_column_name(h)
            for h in tokenize_schema(load_text_or_file(args.column_names_hints_path))
        )
    if args.hints_column_alignment is not None and not hints:
        print(
            "Error: --hints-column-alignment requires --column-names-hints or "
            "--column-names-hints-path.",
            file=sys.stderr,
        )
        sys.exit(1)

    paper_aliases: dict[str, PaperAlias] = {}
    if args.paper_aliases:
        paper_aliases.update(parse_paper_aliases(args.paper_aliases))
    if args.paper_aliases_path:
        paper_aliases.update(
            parse_paper_aliases(load_text_or_file(args.paper_aliases_path))
        )

    load_analyzers, merge_analyzers = build_analyzers(
        use_jaccard=args.jaccard_column_alignment,
        use_column_name_semantic=args.column_name_semantic_alignment,
        use_column_value_semantic=args.column_value_semantic_alignment,
        hints_mode=args.hints_column_alignment,
        threshold=args.column_alignment_threshold,
        language=args.semantic_language,
        aliases=aliases,
        schema=schema,
        hints=hints,
    )

    pretransformers: list[FragmentTransformer] = []
    if args.fix_reversed_column_values:
        pretransformers.append(FragmentValuesReverser(args.semantic_language))
    if args.filter_title_rows:
        pretransformers.append(FilterTitleRowsTransformer())
    if args.strip_leading_row_numbers:
        pretransformers.append(LeadingRowNumberTransformer())
    if args.normalize_punctuation:
        pretransformers.append(NormalizePunctuationTransformer())
    if args.split_conjunction_columns:
        pretransformers.append(SplitColumnTransformer(args.semantic_language))
    pretransformers.append(FilterEmptyRowsTransformer())

    tablesfile_transformer = TRANSFORMER_MAP.get(
        args.transform_tablesfile, NullTablesfileTransformer()
    )

    merge_resultsets(
        args.paths,
        args.output_directory,
        metadata_only=args.metadata_only,
        agreement_method=args.agreement_method,
        drop_empty_columns=args.drop_empty_columns,
        drop_empty_tables=args.drop_empty_tables,
        only_semantic_columns=args.only_semantic_columns,
        remove_header_rows=args.remove_header_rows,
        hints=hints,
        pretty=args.pretty,
        pretransformers=pretransformers,
        load_analyzers=load_analyzers,
        merge_analyzers=merge_analyzers,
        schema=schema,
        postprocessors=postprocessors,
        tablesfile_transformer=tablesfile_transformer,
        workers=args.workers,
        paper_aliases=paper_aliases,
        paper_filter=args.paper,
        export_settings=args.export_settings,
    )


if __name__ == "__main__":
    main()
