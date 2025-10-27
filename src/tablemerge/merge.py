import re
from itertools import zip_longest
from tablevalidate.schema import (
    TablesFile,
    Table,
    TableFragment,
    TableWithFragments,
    Row,
    get_table_fragments,
)


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


def same_row(left: Row, right: Row):
    False


def merge_tablesfiles(tablesfiles: list[TablesFile]) -> TablesFile:
    """
    Process one or more "tables" elements
    """
    if not len(tablesfiles):
        raise ValueError("Must pass at least TablesFile element")

    merged_tables: list[Table] = []

    tables_clusters: list[tuple[Table]] = zip_longest(
        *map(lambda t: t.tables, tablesfiles)
    )
    for tables_cluster in tables_clusters:
        merged_fragments: list[TableFragment] = []
        fragments_clusters: list[tuple[TableFragment]] = zip_longest(
            *map(get_table_fragments, tables_cluster)
        )
        for fragments_cluster in fragments_clusters:
            merged_rows: list[Row] = []

            for index in range(0, len(fragments_cluster) - 2):
                left_fragment = fragments_cluster[index]
                right_fragment = fragments_cluster[index + 1]

                if left_fragment.page != right_fragment.page:
                    raise ValueError("Pages don't match")

                left_rows = left_fragment.rows
                right_rows = right_fragment.rows

                start_right_index = 0

                for left_index in range(0, len(left_rows)):
                    for right_index in range(start_right_index, len(right_rows)):
                        if same_row(left_rows[left_index], right_rows[right_index]):
                            for skipped_row in right_rows[
                                start_right_index:right_index
                            ]:
                                merged_rows.append(skipped_row)
                            merged_rows.append(
                                merge_rows(
                                    left_rows[left_index], right_rows[right_index]
                                )
                            )
                            start_right_index = right_index
                            break
                    merged_rows.append(left_rows[left_index])

            merged_fragments.append(
                TableFragment(rows=merged_rows, page=fragments_cluster[0].page)
            )

        merged_tables.append(TableWithFragments(table_fragments=merged_fragments))

    # # TODO pick all citations
    citation = tablesfiles[0].citation

    return TablesFile(tables=merged_tables, citation=citation)
