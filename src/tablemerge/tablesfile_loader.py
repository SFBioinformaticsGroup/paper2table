import json
from pathlib import Path

from tablevalidate.schema import TablesFile
from tablemerge.merge import filter_title_rows


class TablesFileLoader:
    def load(self, path: Path) -> TablesFile:
        with open(path, "r", encoding="utf-8") as f:
            return filter_title_rows(TablesFile.model_validate(json.load(f)))
