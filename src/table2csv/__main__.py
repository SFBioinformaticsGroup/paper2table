import argparse
import json
from pathlib import Path
import pandas as pd
from utils.table_fragments import get_table_fragments


# TODO reuse function in paper2html
def load_papers(directory: Path):
    papers = {}
    for paper_file in directory.glob("*.tables.json"):
        if paper_file.name == "tables.metadata.json":
            continue
        with open(paper_file, "r", encoding="utf-8") as f:
            papers[paper_file.name] = json.load(f)
    return papers


def build_dataframes(papers):
    csvs = {}
    for basename, tablesfile in papers.items():
        csvs[basename] = []
        for table in tablesfile.get("tables", []):
            fragments = get_table_fragments(table)
            csv_rows = []
            for fragment in fragments:
                page = fragment.get("page", "")
                rows = fragment.get("rows", [])

                for row in rows:
                    row["$page"] = page

            csvs[basename].append(pd.DataFrame(rows))
    return csvs


def save_csv(dataframe, output_file: Path):
    dataframe.to_csv(output_file, index=False)


def main():
    parser = argparse.ArgumentParser(description="Export paper2table tables to csvs")
    parser.add_argument(
        "input_dir", help="Directory with tables.metadata.json and *.tables.json"
    )
    parser.add_argument(
        "-o", "--output-directory", default=".", help="Output directory (default: .)"
    )
    args = parser.parse_args()

    papers = load_papers(Path(args.input_dir))
    Path(args.output_directory).mkdir(parents=True, exist_ok=True)
    for basename, dataframes in build_dataframes(papers).items():
        for index, dataframe in enumerate(dataframes):
            save_csv(
                dataframe,
                Path(args.output_directory)
                / f"{basename.replace(".tables.json", "")}_{index}.csv",
            )


if __name__ == "__main__":
    main()
