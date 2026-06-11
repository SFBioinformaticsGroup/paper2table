from utils.column_names import normalize_column_name
from tablevalidate.schema import (
    TablesFile,
    TableFragment,
    TableWithFragments,
    ColumnValue,
    Row,
)

def value_matches_header(column_name: str, value: ColumnValue) -> bool:
    if value is None:
        return False
    normalized_name = normalize_column_name(column_name)
    if isinstance(value, str):
        return normalize_column_name(value) == normalized_name

    non_empty = [v.value for v in value if v.value.strip()]
    return bool(non_empty) and all(
        normalize_column_name(v) == normalized_name for v in non_empty
    )


def value_matches_hints(value: ColumnValue, hints_set: set[str]) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return normalize_column_name(value.strip()) in hints_set

    return any(
        normalize_column_name(v.value.strip()) in hints_set
        for v in value
        if v.value.strip()
    )


def has_semantic_header_value(row: Row) -> bool:
    return any(
        value_matches_header(col, val)
        for col, val in row.get_columns().items()
        if not Row.is_empty_value(val) and Row.is_semantic_column(col)
    )


def has_hints_header_value(row: Row, hints_set: set[str]) -> bool:
    return any(
        value_matches_hints(val, hints_set)
        for col, val in row.get_columns().items()
        if not Row.is_empty_value(val) and not Row.is_semantic_column(col)
    )


def is_header_row(row: Row, hints: list[str] = []) -> bool:
    return has_semantic_header_value(row) or (
        bool(hints) and has_hints_header_value(row, set(hints))
    )


def filter_header_rows(tablesfile: TablesFile, hints: list[str] = []) -> TablesFile:
    filtered_tables = []
    for table in tablesfile.tables:
        filtered_fragments = []
        for fragment in table.get_table_fragments():
            filtered_rows = [
                row for row in fragment.rows if not is_header_row(row, hints)
            ]
            filtered_fragments.append(
                TableFragment(rows=filtered_rows, page=fragment.page)
            )
        filtered_tables.append(TableWithFragments(table_fragments=filtered_fragments))
    return TablesFile(
        tables=filtered_tables,
        citation=tablesfile.citation,
        metadata=tablesfile.metadata,
        uuid=tablesfile.uuid,
    )



def drop_empty_non_semantic_columns(tablesfile: TablesFile) -> TablesFile:
    filtered_tables = []
    for table in tablesfile.tables:
        filtered_fragments = []
        for fragment in table.get_table_fragments():
            all_cols = Row.column_names(fragment.rows)
            empty_cols = {
                col
                for col in all_cols
                if not Row.is_semantic_column(col)
                and all(
                    Row.is_empty_value(row.get_columns().get(col))
                    for row in fragment.rows
                )
            }
            new_rows = [
                Row(
                    agreement_level_=row.agreement_level_,
                    sources_=row.sources_,
                    row_=row.row_,
                    **{
                        k: v
                        for k, v in row.get_columns().items()
                        if k not in empty_cols
                    },
                )
                for row in fragment.rows
            ]
            filtered_fragments.append(TableFragment(rows=new_rows, page=fragment.page))
        filtered_tables.append(TableWithFragments(table_fragments=filtered_fragments))
    return TablesFile(
        tables=filtered_tables,
        citation=tablesfile.citation,
        metadata=tablesfile.metadata,
        uuid=tablesfile.uuid,
    )


def drop_empty_tables(tablesfile: TablesFile) -> TablesFile:
    filtered_tables = []
    for table in tablesfile.tables:
        fragments = [f for f in table.get_table_fragments() if not f.is_empty()]
        if fragments:
            filtered_tables.append(TableWithFragments(table_fragments=fragments))
    return TablesFile(
        tables=filtered_tables,
        citation=tablesfile.citation,
        metadata=tablesfile.metadata,
        uuid=tablesfile.uuid,
    )


def filter_semantic_columns(tablesfile: TablesFile) -> TablesFile:
    filtered_tables = []
    for table in tablesfile.tables:
        filtered_fragments = []
        for fragment in table.get_table_fragments():
            filtered_rows = [
                Row(
                    agreement_level_=row.agreement_level_,
                    sources_=row.sources_,
                    row_=row.row_,
                    **row.get_semantic_columns(),
                )
                for row in fragment.rows
            ]
            filtered_fragments.append(
                TableFragment(rows=filtered_rows, page=fragment.page)
            )
        filtered_tables.append(TableWithFragments(table_fragments=filtered_fragments))
    return TablesFile(
        tables=filtered_tables,
        citation=tablesfile.citation,
        metadata=tablesfile.metadata,
        uuid=tablesfile.uuid,
    )
