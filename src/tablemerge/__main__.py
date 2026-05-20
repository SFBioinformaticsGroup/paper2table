import argparse
import json
from datetime import datetime as dt
from pathlib import Path
from uuid import uuid4

from tablevalidate.schema import TablesFile

from .merge import (
    merge_tablesfiles,
    filter_semantic_columns,
    MergeError,
    SimpleCountAgreement,
    DistinctReadersAgreement,
)


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
    agreement_method: str = "simple-count",
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
        "agreement_method": agreement_method,
        "sources": sources,
    }

    output_path.mkdir(parents=True, exist_ok=True)
    metadata_out = output_path / "tables.metadata.json"
    with open(metadata_out, "w", encoding="utf-8") as f:
        json.dump(merge_metadata, f, ensure_ascii=False, indent=2)

    print(f"Metadata written to {metadata_out}")
    return merge_metadata


def merge_tablesfiles_paths(
    basename,
    resultset_dirs,
    output_path,
    metadata_map: dict[str, dict],
    agreement,
    only_semantic_columns: bool = False,
    pretty: bool = False,
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
            tablesfiles, agreement=agreement
        )
        if only_semantic_columns:
            merged_tablesfile = filter_semantic_columns(merged_tablesfile)
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
    pretty: bool = False,
):
    output_path = Path(output_dir)
    resultset_metadata = {d: read_resultset_metadata(d) for d in resultset_dirs}

    write_merge_metadata(
        resultset_dirs, output_path, resultset_metadata, agreement_method
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
            pretty=pretty,
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
        "--pretty",
        action="store_true",
        help="Pretty-print merged output files with indentation",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    merge_resultsets(
        args.paths,
        args.output_directory,
        metadata_only=args.metadata_only,
        agreement_method=args.agreement_method,
        only_semantic_columns=args.only_semantic_columns,
        pretty=args.pretty,
    )


if __name__ == "__main__":
    main()
