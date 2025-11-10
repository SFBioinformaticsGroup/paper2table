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


class MergeError(ValueError):
    pass


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


def normalize_row(row: Row, row_agreement: bool = False) -> Row:
    return Row(
        **{
            column: normalize_value(value)
            for column, value in row.get_columns().items()
        },
        agreement_level_=(
            row.get_agreement_level() if row_agreement else row.agreement_level_
        ),
    )


def same_row(left: Row, right: Row) -> bool:
    # TODO compare using a broader similarity criteria
    return normalize_row(left).get_columns() == normalize_row(right).get_columns()


def merge_rows(
    left: Row, right: Row, row_agreement=False, column_agreement=False
) -> Row:
    agreement_level = (
        left.get_agreement_level() + right.get_agreement_level()
        if row_agreement
        else None
    )
    # TODO compute columns agreement
    columns = {
        **normalize_row(left).get_columns(),
        **normalize_row(right).get_columns(),
    }
    return Row(agreement_level_=agreement_level, **columns)


def merge_tablesfiles(
    tablesfiles: list[TablesFile], row_agreement=False, column_agreement=False
) -> TablesFile:
    """
    Process one or more "tables" elements
    """
    if not len(tablesfiles):
        raise MergeError("Must pass at least TablesFile element")

    merged_tables: list[Table] = []

    # ============================
    # Zip tables of the same page
    # ============================

    tables_clusters: list[tuple[Table]] = zip_longest(
        *map(lambda t: t.tables, tablesfiles)
    )
    for tables_cluster in tables_clusters:
        # ==============================
        # Zip fragments of the same page
        # ==============================

        merged_fragments: list[TableFragment] = []
        fragments_clusters = make_fragments_clusters(tables_cluster)

        for fragments_cluster in fragments_clusters.values():

            # =================================
            # Combine rows of the same fragment
            # =================================

            # TODO sort first so longest cluster is the first one
            left_fragment = fragments_cluster[0]
            if not left_fragment:
                raise MergeError(f"no left fragment in {fragments_cluster}")

            table_fragment_builder = TableFragmentBuilder(
                left_fragment, row_agreement, column_agreement
            )

            for right_fragment in fragments_cluster[1:]:
                if not right_fragment:
                    break

                if left_fragment.page != right_fragment.page:
                    raise MergeError(
                        f"Pages don't match: {left_fragment.page} != {right_fragment.page}"
                    )

                right_rows = right_fragment.rows
                left_rows = table_fragment_builder.next_left_rows()
                start_right_index = 0

                for left_row in left_rows:
                    found = False
                    for right_index in range(start_right_index, len(right_rows)):
                        if same_row(left_row, right_rows[right_index]):
                            # add all right rows that are before
                            # the matching row
                            table_fragment_builder.append_skipped(
                                right_rows[start_right_index:right_index]
                            )

                            table_fragment_builder.merge_and_append(
                                left_row,
                                right_rows[right_index],
                            )
                            # update right index so that
                            # new left rows are matched only to rows that
                            # are after the one found
                            start_right_index = right_index + 1
                            found = True
                            break

                    if not found:
                        table_fragment_builder.append_unmatched(left_row)

                table_fragment_builder.append_skipped(right_rows[start_right_index:])

            merged_fragments.append(table_fragment_builder.build())

        merged_tables.append(TableWithFragments(table_fragments=merged_fragments))

    # # TODO pick all citations
    citation = tablesfiles[0].citation

    return TablesFile(tables=merged_tables, citation=citation)


def make_fragments_clusters(tables_cluster: list[Table]):
    fragments_clusters: dict[int, list[TableFragment]] = {}
    for table in tables_cluster:
        for fragment in get_table_fragments(table):
            fragments_clusters.setdefault(fragment.page, []).append(fragment)
    return fragments_clusters


class TableFragmentBuilder:
    rows: list[Row]
    page: int
    row_agreement: bool
    column_agreement: bool

    def __init__(
        self,
        initial_fragment: TableFragment,
        row_agreement: bool,
        column_agreement: bool,
    ):
        self.rows = list(
            map(
                lambda row: normalize_row(row, row_agreement),
                initial_fragment.rows,
            )
        )
        self.page = initial_fragment.page
        self.row_agreement = row_agreement
        self.column_agreement = column_agreement

    def next_left_rows(self):
        rows = self.rows
        self.rows = []
        return list(rows)

    def _append(self, row: Row):
        new = normalize_row(row, self.row_agreement)
        self.rows.append(new)

    def append_skipped(self, rows: list[Row]):
        """
        Append a range of rows, without processing them
        """
        for skipped_row in rows:
            self._append(skipped_row)

    def append_unmatched(self, row: Row):
        """
        Append a row that was not found in the right table
        add it as is, unless it was added as part of
        an skipped range
        """
        if not any(same_row(merged_row, row) for merged_row in self.rows):
            self._append(row)
        else:
            # TODO merge existing and not found
            # and replace it
            pass

    def merge_and_append(self, left: Row, right: Row):
        """
        Merge and add found row
        """
        self._append(
            merge_rows(
                left,
                right,
                row_agreement=self.row_agreement,
                column_agreement=self.column_agreement,
            )
        )

    def build(self):
        return TableFragment(rows=self.rows, page=self.page)
