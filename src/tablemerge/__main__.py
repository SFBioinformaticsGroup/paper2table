import argparse
import json
from pathlib import Path

from .merge import merge_tables


def merge_tables_file(tables_basename, input_dirs, output_path):
    tables_list = []
    # TODO pick longest citation
    citation = None
    for input_directory in input_dirs:
        tables_path = Path(input_directory) / tables_basename
        if tables_path.exists():
            with open(tables_path, "r", encoding="utf-8") as infile:
                data = json.load(infile)
                tables_list.append(data["tables"])
                citation = data.get("citation", citation)

    # TODO add uuids to each row sources
    merged_tables = merge_tables(tables_list)
    merged_data = {"tables": merged_tables, "citation": citation or ""}

    with open(output_path / tables_basename, "w", encoding="utf-8") as outfile:
        json.dump(merged_data, outfile)


def merge_directories(input_dirs: list[str], output_dir: str):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    tables_basenames = set()
    for d in input_dirs:
        for f in Path(d).glob("*.tables.json"):
            tables_basenames.add(f.name)

    for tables_basename in tables_basenames:
        merge_tables_file(tables_basename, input_dirs, output_path)

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
        default="."
    )
    parser.add_argument(
        "paths", nargs="+", help="Input directories containing .tables.json files"
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    merge_directories(args.paths, args.output_directory)


if __name__ == "__main__":
    main()
