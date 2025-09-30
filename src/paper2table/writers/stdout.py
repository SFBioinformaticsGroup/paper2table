import json
from ..tables_protocol import TablesProtocol


def write_tables(tables: TablesProtocol):
    print(json.dumps(tables.to_dict(), ensure_ascii=False))
