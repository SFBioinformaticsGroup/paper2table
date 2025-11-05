import argparse
import json
from pathlib import Path

from .merge import merge_tablesfiles, MergeError

from tablevalidate.schema import TablesFile


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
            tablesfiles, with_row_agreement=True
        )
        print(f"{basename}: MERGED: {len(tablesfiles)} files into {len(merged_tablesfile.tables)} tables")
        with open(output_path / basename, "w", encoding="utf-8") as outfile:
            json.dump(merged_tablesfile.model_dump(), outfile, ensure_ascii=False)
    except MergeError as e:
        print(f"{basename}: MERGE FAILED:", str(e))


def merge_resultsets(resultset_dirs: list[str], output_dir: str):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    tablesfiles_basenames = set()
    for resultset_dir in resultset_dirs:
        for tablesfile in Path(resultset_dir).glob("*.tables.json"):
            tablesfiles_basenames.add(tablesfile.name)

    for basename in sorted(list(tablesfiles_basenames)):
        merge_tablesfiles_paths(basename, resultset_dirs, output_path)

    # TODO
    # merge_metadata(input_dirs, output_path)


def parse_arguments():
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
        "paths", nargs="+", help="Input directories containing .tables.json files"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    merge_resultsets(args.paths, args.output_directory)


if __name__ == "__main__":
    main()
