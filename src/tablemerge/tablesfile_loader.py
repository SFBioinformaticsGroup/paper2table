import json
from pathlib import Path

from tablevalidate.schema import TablesFile
from tablemerge.merge import filter_title_rows


class TablesFileLoader:
    def __init__(self, filter_title_rows: bool = True):
        self.filter_title_rows = filter_title_rows

    @property
    def settings(self) -> dict:
        return {"filter_title_rows": self.filter_title_rows}

    def load(self, path: Path) -> TablesFile:
        with open(path, "r", encoding="utf-8") as f:
            tablesfile = TablesFile.model_validate(json.load(f))
        if self.filter_title_rows:
            tablesfile = filter_title_rows(tablesfile)
        return tablesfile
