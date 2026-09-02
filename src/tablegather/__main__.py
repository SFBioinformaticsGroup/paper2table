import argparse
import json
import sys
from datetime import datetime as dt
from pathlib import Path
from uuid import uuid4

from tablevalidate.schema import TablesFile
from utils.cli import add_postprocessor_args, build_postprocessors_from_args
from utils.column_schema import ColumnSchema, try_parse_schema
from utils.table_fragments import load_papers

from .collect import gather_tablesfiles


def read_resultset_metadata(resultset_dir: str) -> dict:
    try:
        with open(
            Path(resultset_dir) / "tables.metadata.json", "r", encoding="utf-8"
        ) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def compute_sources(
    tablesfiles_with_paths: list[tuple[TablesFile, Path]],
    directory_metadata: dict[str, dict],
) -> list[dict]:
    seen_citations: set[str] = set()
    sources = []
    for tablesfile, path in tablesfiles_with_paths:
        citation = tablesfile.citation
        if not citation or isinstance(citation, list):
            citation = Path(path.stem).stem
        if citation in seen_citations:
            continue
        seen_citations.add(citation)
        source: dict = {"path": str(path)}
        if tablesfile.uuid:
            source["uuid"] = tablesfile.uuid
        dir_meta = directory_metadata.get(str(path.parent), {})
        if "reader" in dir_meta:
            source["reader"] = dir_meta["reader"]
        sources.append(source)
    return sources


def write_gather_metadata(
    output_dir: Path, sources: list[dict], settings: dict
) -> None:
    metadata = {
        "reader": "tablegather",
        "uuid": str(uuid4()),
        "datetime": dt.now().isoformat(),
        "settings": settings,
        "sources": sources,
    }
    metadata_out = output_dir / "tables.metadata.json"
    with open(metadata_out, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"Metadata written to {metadata_out}")


def tablegather_schema(
    schema: ColumnSchema | None,
    citation_column: str,
    path_column: str | None,
) -> ColumnSchema | None:
    if schema is None:
        return None
    gather_columns: dict[str, type] = {citation_column: str}
    if path_column:
        gather_columns[path_column] = str
    return ColumnSchema(dict(schema.definitions()) | gather_columns)


def main():
    parser = argparse.ArgumentParser(
        description="Collect all .tables.json files from one or more directories into a single table."
    )
    parser.add_argument("resultset_dirs", nargs="+", metavar="RESULTSET_DIR")
    parser.add_argument(
        "--key-columns",
        nargs="+",
        metavar="COLUMN",
        help="Column names to sort gathered rows by",
    )
    parser.add_argument(
        "--citation-column",
        default="citation",
        metavar="NAME",
        help="Column name added to each row for the source citation (default: citation)",
    )
    parser.add_argument(
        "--path-column",
        metavar="NAME",
        help="Column name added to each row for the source file path (omit to disable)",
    )
    parser.add_argument(
        "--convergence",
        choices=["none", "rows", "fragments", "tables"],
        default="none",
        metavar="LEVEL",
        help="Convergence filter: none (default), rows, fragments, tables",
    )
    parser.add_argument(
        "-o",
        "--output-directory",
        metavar="DIR",
        help="Directory to write gathered.tables.json and tables.metadata.json (default: stdout)",
    )
    parser.add_argument("--pretty", action="store_true", help="Indent JSON output")
    add_postprocessor_args(parser)

    args = parser.parse_args()

    schema: ColumnSchema | None = try_parse_schema(args)
    schema = tablegather_schema(schema, args.citation_column, args.path_column)
    postprocessors = build_postprocessors_from_args(args, schema)

    key_columns: list[str] = args.key_columns or []

    directory_metadata = {d: read_resultset_metadata(d) for d in args.resultset_dirs}

    tablesfiles_with_paths: list[tuple[TablesFile, Path]] = []
    for directory in args.resultset_dirs:
        papers = load_papers(Path(directory))
        for name, tablesfile in papers.items():
            tablesfiles_with_paths.append((tablesfile, Path(directory) / name))

    result = gather_tablesfiles(
        tablesfiles_with_paths,
        args.citation_column,
        key_columns,
        path_column=args.path_column,
        convergence=args.convergence,
    )

    for postprocessor in postprocessors:
        result = postprocessor.postprocess(result)

    indent = 2 if args.pretty else None
    output = result.model_dump_json(indent=indent, exclude_none=True)

    if args.output_directory:
        output_dir = Path(args.output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "gathered.tables.json"
        output_file.write_text(output, encoding="utf-8")
        print(f"Written to {output_file}")
        sources = compute_sources(tablesfiles_with_paths, directory_metadata)
        settings = {
            "citation_column": args.citation_column,
            "key_columns": key_columns,
            "path_column": args.path_column,
            "convergence": args.convergence,
        }
        write_gather_metadata(output_dir, sources, settings)
    else:
        sys.stdout.write(output)
        sys.stdout.write("\n")
