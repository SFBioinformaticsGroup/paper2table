import json
import os
from typing import Literal, Optional
from uuid import UUID, uuid4
from datetime import datetime as dt

from paper2table.tables_reader import TablesReader

from . import file


class TablemergeMetadata:
    reader: Literal["agent", "hybrid", "pdfplumber", "camelot"]
    model: Optional[str]
    datetime: dt
    uuid: UUID

    def __init__(self, reader: str, model: Optional[str]):
        self.reader = reader
        self.model = model
        self.uuid = uuid4()
        self.datetime = dt.now()

    def get_reader(self):
        if self.reader == "agent":
            return self.model
        elif self.reader == "hybrid":
            return f"hybrid-pdfplumber-{self.model}"
        return self.reader

    def to_dict(self):
        return {
            "reader": self.get_reader(),
            "uuid": str(self.uuid),
            "datetime": self.datetime.isoformat(),
        }


def write_tables(
    tables: TablesReader,
    paper_path: str,
    output_directory: str,
    metadata: TablemergeMetadata,
):
    tablemerge_path = os.path.join(output_directory, str(metadata.uuid))
    metadata_path = os.path.join(tablemerge_path, "tables.metadata.json")

    os.makedirs(tablemerge_path, exist_ok=True)

    if not os.path.exists(metadata_path):
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, ensure_ascii=False)

    file.write_tables(tables, paper_path, tablemerge_path)
