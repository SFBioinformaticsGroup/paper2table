def get_table_fragments(table: dict) -> list[dict]:
    return table["table_fragments"] if "table_fragments" in table else [table]
