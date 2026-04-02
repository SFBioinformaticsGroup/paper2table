import argparse
import json
from datetime import datetime as dt
from pathlib import Path
from uuid import uuid4

from tablevalidate.schema import TablesFile

from .merge import merge_tablesfiles, MergeError


def generate_merge_metadata(resultset_dirs: list[str], output_path: Path):
    sources = []
    for resultset_dir in resultset_dirs:
        source = {"path": resultset_dir}
        metadata_file = Path(resultset_dir) / "tables.metadata.json"
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
                if "uuid" in meta:
                    source["uuid"] = meta["uuid"]
                if "reader" in meta:
                    source["reader"] = meta["reader"]
        sources.append(source)

    metadata = {
        "reader": "tablemerge",
        "uuid": str(uuid4()),
        "datetime": dt.now().isoformat(),
        "sources": sources,
    }

    output_path.mkdir(parents=True, exist_ok=True)
    metadata_out = output_path / "tablemerge.metadata.json"
    with open(metadata_out, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print("Metadata written to ", metadata_out)
    return metadata


def merge_tablesfiles_paths(basename, resultset_dirs, output_path):
    """
    Merge all the TablesFile of the same basename
    in the given resultset directories
    """
    tablesfiles: list[TablesFile] = []
    for resultset_dir in resultset_dirs:
        tables_path = Path(resultset_dir) / basename
        if tables_path.exists():
            with open(tables_path, "r", encoding="utf-8") as tablesfile:
                data = json.load(tablesfile)
                tablesfile = TablesFile.model_validate(data)
                tablesfiles.append(tablesfile)

    # TODO add uuids to each row sources
    sizes = [len(tablesfile.tables) for tablesfile in tablesfiles]

    if not any(size > 0 for size in sizes):
        print(
            f"{basename}: MERGE SKIPPED: All tables are empty",
        )
        return

    try:
        merged_tablesfile: TablesFile = merge_tablesfiles(
            tablesfiles, row_agreement=True
        )
        print(
            f"{basename}: MERGED: {len(tablesfiles)} files"
            f" into {len(merged_tablesfile.tables)} tables"
        )
        with open(output_path / basename, "w", encoding="utf-8") as outfile:
            json.dump(merged_tablesfile.model_dump(), outfile, ensure_ascii=False)
    except MergeError as e:
        print(f"{basename}: MERGE FAILED:", str(e))


def merge_resultsets(resultset_dirs: list[str], output_dir: str, metadata_only=False):
    output_path = Path(output_dir)

    generate_merge_metadata(resultset_dirs, output_path)

    if metadata_only:
        return

    output_path.mkdir(parents=True, exist_ok=True)

    tablesfiles_basenames = set()
    for resultset_dir in resultset_dirs:
        for tablesfile in Path(resultset_dir).glob("*.tables.json"):
            tablesfiles_basenames.add(tablesfile.name)

    for basename in sorted(list(tablesfiles_basenames)):
        merge_tablesfiles_paths(basename, resultset_dirs, output_path)


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
    return parser.parse_args()


def main():
    args = parse_args()
    merge_resultsets(
        args.paths, args.output_directory, metadata_only=args.metadata_only
    )


if __name__ == "__main__":
    main()
