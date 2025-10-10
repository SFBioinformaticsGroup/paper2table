import re
from utils.table_fragments import get_table_fragments

def normalize_value(value):
    return (
        re.sub(r"\s+", " ", value.strip()).lower() if isinstance(value, str) else value
    )


def normalize_row(row):
    return {column: normalize_value(value) for column, value in row.items()}


def merge_rows_unique(rows, seen):
    merged = []
    for row in rows:
        normalized = normalize_row(row)
        row_tuple = tuple(sorted(normalized.items()))
        if row_tuple not in seen:
            seen.add(row_tuple)
            merged.append(normalized)
    return merged


def intercalate_rows(list_of_rows):
    merged = []
    seen = set()
    iterators = [iter(rows) for rows in list_of_rows]
    finished = False
    while not finished:
        finished = True
        for it in iterators:
            try:
                row = next(it)
                merged.extend(merge_rows_unique([row], seen))
                finished = False
            except StopIteration:
                continue
    return merged


def merge_tables(tables_list):


    if not len(tables_list):
      raise ValueError("Must pass at least one element")

    # TODO prevent duplicate values in the same input table
    pages = {}
    for tables in tables_list:
        # TODO detect if we should convert multiple one-fragment tables
        # in just one table with multiple fragments
        for table in tables:
            for fragment in get_table_fragments(table):
                page = fragment.get("page")
                pages.setdefault(page, []).append(fragment["rows"])

    merged_tables = []
    for page, rows_list in pages.items():
        # TODO detect if we should convert multiple one-fragment tables
        # in just one table with multiple fragments
        merged_rows = intercalate_rows(rows_list)
        fragment = {"rows": merged_rows}
        if page is not None:
            fragment["page"] = page
        merged_tables.append(fragment)
    return merged_tables
