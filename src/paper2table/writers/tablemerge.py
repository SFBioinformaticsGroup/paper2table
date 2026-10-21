import json
import os
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4
from datetime import datetime as dt

from paper2table.tables_reader import TablesReader
from utils.jsonc import load_jsonc

from . import file

type Reader = Literal["agent", "pdfplumber", "camelot", "img2table", "pymupdf"]

class TablemergeMetadata:
    reader: Reader
    model: Optional[str]
    datetime: dt
    hybrid: bool
    id: str

    def __init__(
        self,
        reader: Reader,
        model: Optional[str],
        hybrid=False,
        id: Optional[str] = None,
    ):
        self.reader = reader
        self.model = model
        self.hybrid = hybrid
        self.id = id if id is not None else str(uuid4())
        self.datetime = dt.now()

    def get_reader(self):
        if self.reader == "agent":
            return self.model
        if self.hybrid:
            return f"hybrid-{self.reader}-{self.model}"
        return self.reader

    def to_dict(self):
        return {
            "reader": self.get_reader(),
            "id": self.id,
            "datetime": self.datetime.isoformat(),
        }


def load_metadata(output_directory: str, id: str) -> dict:
    # TODO refactor: this code is everywhere
    path = os.path.join(output_directory, id, "tables.metadata.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No resultset found at {path}")
    return load_jsonc(Path(path))


def write_tables(
    tables: TablesReader,
    paper_path: str,
    output_directory: str,
    metadata: TablemergeMetadata,
    indent: int | None = None,
):
    tablemerge_path = os.path.join(output_directory, metadata.id)
    metadata_path = os.path.join(tablemerge_path, "tables.metadata.json")

    os.makedirs(tablemerge_path, exist_ok=True)

    if not os.path.exists(metadata_path):
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, ensure_ascii=False)

    file.write_tables(tables, paper_path, tablemerge_path, indent=indent)
