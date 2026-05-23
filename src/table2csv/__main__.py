import argparse
from pathlib import Path
import pandas as pd
from utils.table_fragments import load_papers
from tablevalidate.schema import TablesFile


def build_dataframes(papers: dict[str, TablesFile]) -> dict[str, list[pd.DataFrame]]:
    csvs: dict[str, list[pd.DataFrame]] = {}
    for basename, tablesfile in papers.items():
        csvs[basename] = []
        for table in tablesfile.tables:
            rows = []
            for fragment in table.get_table_fragments():
                for row in fragment.rows:
                    rows.append({**dict(row.get_columns()), "$page": fragment.page})
            csvs[basename].append(pd.DataFrame(rows))
    return csvs


def save_csv(dataframe: pd.DataFrame, output_file: Path) -> None:
    dataframe.to_csv(output_file, index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export paper2table tables to csvs")
    parser.add_argument(
        "input_dir", help="Directory with tables.metadata.json and *.tables.json"
    )
    parser.add_argument(
        "-o", "--output-directory", default=".", help="Output directory (default: .)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    papers = load_papers(Path(args.input_dir))
    Path(args.output_directory).mkdir(parents=True, exist_ok=True)
    for basename, dataframes in build_dataframes(papers).items():
        for index, dataframe in enumerate(dataframes):
            save_csv(
                dataframe,
                Path(args.output_directory)
                / f"{basename.replace('.tables.json', '')}_{index}.csv",
            )


if __name__ == "__main__":
    main()
