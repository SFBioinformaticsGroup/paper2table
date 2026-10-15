import json
from ..tables_reader import TablesReader


def write_tables(tables: TablesReader, indent: int | None = None):
    print(json.dumps(tables.to_dict(), ensure_ascii=False, indent=indent))
