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


def normalize_str_value(value: str):
    return re.sub(r"\s+", " ", value.strip()).lower()


def normalize_value(value: str | list[ValueWithAgreement]) -> str:
    if isinstance(value, str):
        return normalize_str_value(value)
    elif isinstance(value, list):
        return [
            ValueWithAgreement(
                value=normalize_str_value(value_with_agreement.value),
                agreement_level=value_with_agreement.agreement_level,
            )
            for value_with_agreement in value
        ]
    else:
        return value


def normalize_row(row: Row) -> Row:
    return Row(
        **{
            column: normalize_value(value)
            for column, value in row.get_columns().items()
        },
        agreement_level_=row.agreement_level_
    )


def same_row(left: Row, right: Row) -> bool:
    # TODO compare using a broader similarity criteria
    return normalize_row(left).get_columns() == normalize_row(right).get_columns()


def merge_rows(left: Row, right: Row) -> Row:
    # TODO merge it fully
    # and optionally normalize values
    return normalize_row(left)


def merge_tablesfiles(
    tablesfiles: list[TablesFile], with_row_agreement=False, with_column_agreement=False
) -> TablesFile:
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

            # TODO sort first so longest cluster is the first one
            left_fragment = fragments_cluster[0]
            merged_rows: list[Row] = list(map(normalize_row, left_fragment.rows))

            for right_fragment in fragments_cluster[1:]:

                if left_fragment.page != right_fragment.page:
                    raise ValueError("Pages don't match")

                right_rows = right_fragment.rows
                left_rows = list(merged_rows)
                merged_rows = []
                start_right_index = 0

                for left_row in left_rows:
                    found = False
                    for right_index in range(start_right_index, len(right_rows)):
                        if same_row(left_row, right_rows[right_index]):
                            # add all right rows that are before
                            # the matching row
                            for skipped_row in right_rows[
                                start_right_index:right_index
                            ]:
                                merged_rows.append(normalize_row(skipped_row))

                            # merge and add found row
                            merged_rows.append(
                                merge_rows(left_row, right_rows[right_index])
                            )
                            # update right index so that
                            # new left rows are matched only to rows that
                            # are after the one found
                            start_right_index = right_index + 1
                            found = True
                            break

                    if not found:
                        # row was not found in the right table
                        # add it as is, unless it was added as part of
                        # an skipped range
                        if not any(
                            same_row(merged_row, left_row) for merged_row in merged_rows
                        ):
                            merged_rows.append(normalize_row(left_row))
                        else:
                            # TODO merge existing and not found
                            # and replace it
                            pass

                for skipped_row in right_rows[start_right_index:]:
                    merged_rows.append(normalize_row(skipped_row))

            merged_fragments.append(
                TableFragment(rows=merged_rows, page=fragments_cluster[0].page)
            )

        merged_tables.append(TableWithFragments(table_fragments=merged_fragments))

    # # TODO pick all citations
    citation = tablesfiles[0].citation

    return TablesFile(tables=merged_tables, citation=citation)
