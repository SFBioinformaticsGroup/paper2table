import argparse
import json
from pathlib import Path

from .merge import merge_tables_list


def merge_tablesfiles(basename, resultset_dirs, output_path):
    """
    Merge all the TablesFile of the same basename
    in the given resultset directories
    """
    tables_list = []
    # TODO pick longest citation
    citation = None
    for resultset_dir in resultset_dirs:
        tables_path = Path(resultset_dir) / basename
        if tables_path.exists():
            with open(tables_path, "r", encoding="utf-8") as tablesfile:
                data = json.load(tablesfile)
                tables_list.append(data["tables"])
                citation = data.get("citation", citation)

    # TODO add uuids to each row sources
    merged_tables = merge_tables_list(tables_list)
    merged_data = {"tables": merged_tables, "citation": citation or ""}

    with open(output_path / basename, "w", encoding="utf-8") as outfile:
        json.dump(merged_data, outfile, ensure_ascii=False)


def merge_resultsets(resultset_dirs: list[str], output_dir: str):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    tablesfiles_basenames = set()
    for resultset_dir in resultset_dirs:
        for tablesfile in Path(resultset_dir).glob("*.tables.json"):
            tablesfiles_basenames.add(tablesfile.name)

    for basename in tablesfiles_basenames:
        merge_tablesfiles(basename, resultset_dirs, output_path)

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
