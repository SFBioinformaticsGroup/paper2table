import json
import os
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime as dt

from . import file

class TablemergeMetadata:
    reader: str
    model: Optional[str]
    datetime: dt
    uuid: UUID

    def __init__(self, reader: str, model: Optional[str]):
        self.reader = reader
        self.model = model
        self.uuid = uuid4()
        self.datetime = dt.now()

    def to_dict(self):
        return {
            "reader": self.model if self.reader == "agent" else self.reader,
            "uuid": str(self.uuid),
            "datetime": self.datetime.isoformat(),
        }


def write_tables(
    tables: dict,
    paper_path: str,
    output_directory: str,
    metadata: TablemergeMetadata,
):
    tablemerge_path = os.path.join(output_directory, str(metadata.uuid))
    metadata_path = os.path.join(tablemerge_path, "tables.metadata.json")

    os.makedirs(tablemerge_path, exist_ok=True)

    if not os.path.exists(metadata_path):
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f)

    file.write_tables(tables, paper_path, tablemerge_path)
