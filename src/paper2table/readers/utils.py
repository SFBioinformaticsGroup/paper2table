from utils import normalize_name

type Row = list[str | None]

def first_row_is_table_header(rows: list[Row], column_names_hints: list[str]):
    return (
        rows
        and column_names_hints
        and any(normalize_name(key) in column_names_hints for key in rows[0])
    )
