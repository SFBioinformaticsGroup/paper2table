import json
import os
import logging

from paper2table.tables_reader import TablesReader

_logger = logging.getLogger("pape2table")


def write_tables(reader: TablesReader, paper_path: str, output_directory: str):
    tables_path = os.path.join(
        output_directory,
        os.path.basename(paper_path).replace(".pdf", ".tables.json"),
    )

    if not reader.tables:
        _logger.warning(f"no tables could be extracted from {paper_path}")
        return

    with open(tables_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(reader.to_dict(), ensure_ascii=False))
