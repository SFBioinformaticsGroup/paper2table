import re
from utils.table_fragments import get_table_fragments
from paper2table.tables_protocol import TablesProtocol

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


def preprocess_tables_list(tables_list):
    new_tables_list = []
    for tables in tables_list:
        new_tables = []
        new_tables_list.append(new_tables)

        previous_page = None
        previous_fragments_count = None
        for table in tables:
            fragments = get_table_fragments(table)
            if (
                previous_page  # not first page
                and len(fragments) == 1  # only one fragment
                and fragments[0]["page"] - 1 == previous_page  # correlative pages
                and (
                    previous_fragments_count == 1
                )  # also only one fragment in previous page
            ):
                new_tables[-1]["table_fragments"].append(fragments)
            else:
                new_tables.append({"table_fragments": fragments})

            previous_page = fragments[-1]["page"]
            previous_fragments_count = len(fragments)

    return new_tables


def merge_tables_list(tables_list: list[list[dict]]):
    """
    Process one or more "tables" elements
    """
    if not len(tables_list):
        raise ValueError("Must pass at least TablesFile element")

    preprocessed_tables_list = preprocess_tables_list(tables_list)
    #print(preprocess_tables_list)

    # TODO prevent duplicate values in the same input table
    pages = {}
    for tables in preprocessed_tables_list:
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
