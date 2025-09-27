import json
import os

from paper2table.tables_protocol import TablesProtocol


def write_tables(tables: TablesProtocol, paper_path: str, output_directory: str):
    tables_path = os.path.join(
        output_directory,
        os.path.basename(paper_path).replace("pdf", "tables.json"),
    )
    with open(tables_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(tables.to_dict()))
