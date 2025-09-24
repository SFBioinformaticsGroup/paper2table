import json
import os


def write_tables(tables: dict, paper_path: str, output_directory_path: str):
    tables_path = os.path.join(
        output_directory_path,
        os.path.basename(paper_path).replace("pdf", "tables.json"),
    )
    with open(tables_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(tables))
