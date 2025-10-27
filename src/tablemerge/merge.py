import re
from itertools import zip_longest
from tablevalidate.schema import (
    TablesFile,
    Table,
    TableFragment,
    TableWithFragments,
    ValueWithAgreement,
    Row,
    get_table_fragments,
)


def normalize_value(value: str | list[ValueWithAgreement]) -> str:
    # TODO handle valueWithAgreement
    return (
        re.sub(r"\s+", " ", value.strip()).lower() if isinstance(value, str) else value
    )


def normalize_row(row: Row) -> Row:
    return Row(
        **{
            column: normalize_value(value)
            for column, value in row.get_columns().items()
        }
    )


def same_row(left: Row, right: Row) -> bool:
    # TODO compare using a broader similarity criteria
    return normalize_row(left).get_columns() == normalize_row(right).get_columns()


def merge_rows(left: Row, right: Row) -> Row:
    # TODO merge it fully
    # and optionally normalize values
    return normalize_row(left)


def merge_tablesfiles(tablesfiles: list[TablesFile]) -> TablesFile:
    """
    Process one or more "tables" elements
    """
    if not len(tablesfiles):
        raise ValueError("Must pass at least TablesFile element")

    merged_tables: list[Table] = []

    # ============================
    # Zip tables of the same page
    # ============================

    tables_clusters: list[tuple[Table]] = zip_longest(
        *map(lambda t: t.tables, tablesfiles)
    )
    for tables_cluster in tables_clusters:
        # TODO validate all the fragments in the cluster
        # start in the same page

        # ==============================
        # Zip fragments of the same page
        # ==============================

        merged_fragments: list[TableFragment] = []
        fragments_clusters: list[tuple[TableFragment]] = zip_longest(
            *map(get_table_fragments, tables_cluster)
        )
        for fragments_cluster in fragments_clusters:

            # =================================
            # Combine rows of the same fragment
            # =================================

            left_fragment = fragments_cluster[0]
            merged_rows: list[Row] = list(map(normalize_row, left_fragment.rows))

            for right_fragment in fragments_cluster[1:]:

                if left_fragment.page != right_fragment.page:
                    raise ValueError("Pages don't match")

                right_rows = right_fragment.rows
                left_rows = list(merged_rows)
                start_right_index = 0

                for left_row in left_rows:
                    for right_index in range(start_right_index, len(right_rows)):
                        if same_row(left_row, right_rows[right_index]):
                            for skipped_row in right_rows[
                                start_right_index:right_index
                            ]:
                                merged_rows.append(normalize_row(skipped_row))
                            merged_rows.append(
                                merge_rows(left_row, right_rows[right_index])
                            )
                            start_right_index = right_index
                            break
                    merged_rows.append(normalize_row(left_row))

            merged_fragments.append(
                TableFragment(rows=merged_rows, page=fragments_cluster[0].page)
            )

        merged_tables.append(TableWithFragments(table_fragments=merged_fragments))

    # # TODO pick all citations
    citation = tablesfiles[0].citation

    return TablesFile(tables=merged_tables, citation=citation)
