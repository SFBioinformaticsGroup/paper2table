from collections.abc import Sequence
from itertools import zip_longest
from typing import Protocol
from unidecode import unidecode
from utils.rows import is_empty_value, normalize_str_value
from tablevalidate.schema import (
    TablesFile,
    Table,
    TableFragment,
    TableWithFragments,
    ValueWithAgreement,
    ColumnValue,
    Row,
)
from tablemerge.columns_aligner import ColumnAligner
from tablemerge.analyzers import Analyzer
from tablemerge.value_transformer import NullValueTransformer, ValueTransformer


def value_matches_header(column_name: str, value: ColumnValue) -> bool:
    normalized_name = normalize_str_value(column_name)
    if isinstance(value, str):
        return normalize_str_value(value) == normalized_name
    non_empty = [v.value for v in value if v.value.strip()]
    return bool(non_empty) and all(
        normalize_str_value(v) == normalized_name for v in non_empty
    )


def is_header_row(row: Row) -> bool:
    non_empty_pairs = [
        (column_name, value)
        for column_name, value in row.get_columns().items()
        if not is_empty_value(value) and Row.is_semantic_column(column_name)
    ]
    return any(
        value_matches_header(column_name, value)
        for column_name, value in non_empty_pairs
    )


def filter_header_rows(tablesfile: TablesFile) -> TablesFile:
    filtered_tables = []
    for table in tablesfile.tables:
        filtered_fragments = []
        for fragment in table.get_table_fragments():
            filtered_rows = [row for row in fragment.rows if not is_header_row(row)]
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


def filter_semantic_columns(tablesfile: TablesFile) -> TablesFile:
    filtered_tables = []
    for table in tablesfile.tables:
        filtered_fragments = []
        for fragment in table.get_table_fragments():
            filtered_rows = [
                Row(
                    agreement_level_=row.agreement_level_,
                    sources_=row.sources_,
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


class Agreement(Protocol):
    def calculate_level(self, left: Row, right: Row) -> int: ...


def is_agent_reader(reader: str | None) -> bool:
    if not reader:
        return True
    if reader in ("pdfplumber", "camelot", "pymupdf"):
        return False
    if reader.startswith("hybrid-"):
        return False
    return True


class SimpleCountAgreement:
    def calculate_level(self, left: Row, right: Row) -> int:
        return left.get_agreement_level() + right.get_agreement_level()


class DistinctReadersAgreement:
    def __init__(self, uuid_to_reader: dict[str, str]):
        self.uuid_to_reader = uuid_to_reader

    def calculate_level(self, left: Row, right: Row) -> int:
        sources = list(dict.fromkeys((left.sources_ or []) + (right.sources_ or [])))
        agent_count = 0
        non_agent_readers: set[str] = set()
        for uuid in sources:
            reader = self.uuid_to_reader.get(uuid)
            if is_agent_reader(reader):
                agent_count += 1
            elif reader is not None:
                non_agent_readers.add(reader)
        return max(1, agent_count + len(non_agent_readers))


class MergeError(ValueError):
    pass


def normalize_value(value: ColumnValue, transformer: ValueTransformer) -> ColumnValue:
    if isinstance(value, str):
        return normalize_str_value(transformer.transform(value))
    if isinstance(value, list):
        return [
            ValueWithAgreement(
                value=normalize_str_value(
                    transformer.transform(value_with_agreement.value)
                ),
                agreement_level=value_with_agreement.agreement_level,
            )
            for value_with_agreement in value
        ]
    return value


def normalize_row(
    row: Row,
    row_agreement: bool = False,
    transformer: ValueTransformer = NullValueTransformer(),
) -> Row:
    return Row(
        **{
            column: normalize_value(value, transformer)
            for column, value in row.get_columns().items()
        },
        agreement_level_=(
            row.get_agreement_level() if row_agreement else row.agreement_level_
        ),
        sources_=row.sources_,
    )


def transliterate_value(value: ColumnValue) -> ColumnValue:
    if isinstance(value, str):
        return unidecode(value)
    if isinstance(value, list):
        return [
            ValueWithAgreement(
                value=unidecode(v.value), agreement_level=v.agreement_level
            )
            for v in value
        ]
    return value


def same_row(left: Row, right: Row, transformer: ValueTransformer) -> bool:
    # TODO compare using a broader similarity criteria
    left_columns = normalize_row(left, False, transformer).get_columns()
    right_columns = normalize_row(right, False, transformer).get_columns()
    return {k: transliterate_value(v) for k, v in left_columns.items()} == {
        k: transliterate_value(v) for k, v in right_columns.items()
    }


def merge_rows(
    left: Row,
    right: Row,
    agreement: Agreement = SimpleCountAgreement(),
    column_agreement: bool = False,
    transformer: ValueTransformer = NullValueTransformer(),
) -> Row:
    agreement_level = agreement.calculate_level(left, right)

    if column_agreement:
        columns = merge_columns_with_agreement(left, right, transformer)
    else:
        columns = merge_columns_without_agreement(left, right, transformer)

    left_sources = left.sources_ or []
    right_sources = right.sources_ or []
    sources = list(dict.fromkeys(left_sources + right_sources)) or None

    return Row(agreement_level_=agreement_level, sources_=sources, **columns)


def merge_columns_without_agreement(
    left: Row, right: Row, transformer: ValueTransformer
):
    return {
        **normalize_row(right, False, transformer).get_columns(),
        **normalize_row(left, False, transformer).get_columns(),
    }


def merge_columns_with_agreement(left: Row, right: Row, transformer: ValueTransformer):
    column_values: dict[str, dict[str, int]] = {}
    for row in [left, right]:
        for column_name, column_value in (
            normalize_row(row, False, transformer).get_columns().items()
        ):
            values = column_values.setdefault(column_name, {})
            values_with_agreement = to_values_with_agreement(column_value)

            for value_with_agreement in values_with_agreement:
                value = value_with_agreement.value
                if value in values:
                    values[value] += value_with_agreement.agreement_level
                else:
                    values[value] = value_with_agreement.agreement_level
    return {
        column_name: [
            ValueWithAgreement(value=column_value, agreement_level=agreement_level)
            for column_value, agreement_level in column_values.items()
        ]
        for column_name, column_values in column_values.items()
    }


def to_values_with_agreement(column_value: ColumnValue):
    return (
        [ValueWithAgreement(value=column_value, agreement_level=1)]
        if isinstance(column_value, str)
        else column_value
    )


def merge_tablesfiles(
    tablesfiles: list[TablesFile],
    agreement: Agreement = SimpleCountAgreement(),
    column_agreement=False,
    analyzers: list[Analyzer] = [],
    transformer: ValueTransformer = NullValueTransformer(),
) -> TablesFile:
    """
    Process one or more "tables" elements
    """
    if not tablesfiles:
        raise MergeError("Must pass at least TablesFile element")

    merged_tables: list[Table] = []

    # ============================
    # Zip tables of the same page
    # ============================

    tables_clusters = list(zip_longest(*map(lambda t: t.tables, tablesfiles)))
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

            first_right = next(
                (f for f in fragments_cluster[1:] if f is not None), None
            )
            aligner = ColumnAligner(
                left_fragment,
                first_right if analyzers else None,
                analyzers=analyzers,
            )
            left_fragment = TableFragment(
                rows=[aligner.rename_row(r) for r in left_fragment.rows],
                page=left_fragment.page,
            )

            table_fragment_builder = TableFragmentBuilder(
                left_fragment,
                tablesfiles[0].uuid,
                agreement,
                column_agreement,
                transformer,
            )

            for right_fragment, right_tablesfile in zip(
                fragments_cluster[1:], tablesfiles[1:]
            ):
                if not right_fragment:
                    break

                if left_fragment.page != right_fragment.page:
                    raise MergeError(
                        f"Pages don't match: {left_fragment.page} != {right_fragment.page}"
                    )

                right_uuid = right_tablesfile.uuid
                right_rows = [aligner.rename_row(r) for r in right_fragment.rows]
                left_rows = table_fragment_builder.next_left_rows()
                start_right_index = 0

                for left_row in left_rows:
                    found = False
                    for right_index in range(start_right_index, len(right_rows)):
                        if same_row(left_row, right_rows[right_index], transformer):
                            table_fragment_builder.append_skipped(
                                right_rows[start_right_index:right_index], right_uuid
                            )

                            right_row = right_rows[right_index].model_copy(
                                update={
                                    "sources_": [right_uuid] if right_uuid else None
                                }
                            )
                            table_fragment_builder.merge_and_append(left_row, right_row)
                            # update right index so that
                            # new left rows are matched only to rows that
                            # are after the one found
                            start_right_index = right_index + 1
                            found = True
                            break

                    if not found:
                        table_fragment_builder.append_unmatched(left_row)

                table_fragment_builder.append_skipped(
                    right_rows[start_right_index:], right_uuid
                )

            merged_fragments.append(table_fragment_builder.build())

        merged_tables.append(TableWithFragments(table_fragments=merged_fragments))

    # # TODO pick all citations
    citation = tablesfiles[0].citation

    return TablesFile(tables=merged_tables, citation=citation)


def make_fragments_clusters(tables_cluster: Sequence[Table | None]):
    fragments_clusters: dict[int, list[TableFragment]] = {}
    for table in tables_cluster:
        if table is None:
            continue
        for fragment in table.get_table_fragments():
            fragments_clusters.setdefault(fragment.page, []).append(fragment)
    return fragments_clusters


class TableFragmentBuilder:
    rows: list[Row]
    page: int
    agreement: Agreement
    column_agreement: bool
    transformer: ValueTransformer

    def __init__(
        self,
        initial_fragment: TableFragment,
        initial_uuid: str | None,
        agreement: Agreement,
        column_agreement: bool,
        transformer: ValueTransformer,
    ):
        self.agreement = agreement
        self.column_agreement = column_agreement
        self.transformer = transformer
        self.page = initial_fragment.page
        do_agreement = agreement is not None
        self.rows = [
            row.model_copy(
                update={"sources_": [initial_uuid] if initial_uuid else None}
            )
            for row in map(
                lambda r: normalize_row(r, do_agreement, transformer),
                initial_fragment.rows,
            )
        ]

    def next_left_rows(self):
        rows = self.rows
        self.rows = []
        return list(rows)

    def _append(self, row: Row):
        new = normalize_row(row, self.agreement is not None, self.transformer)
        self.rows.append(new)

    def append_skipped(self, rows: list[Row], source_uuid: str | None):
        """
        Append a range of rows, without processing them
        """
        for skipped_row in rows:
            stamped = skipped_row.model_copy(
                update={"sources_": [source_uuid] if source_uuid else None}
            )
            self._append(stamped)

    def append_unmatched(self, row: Row):
        """
        Append a row that was not found in the right table
        add it as is, unless it was added as part of
        an skipped range
        """
        if not any(
            same_row(merged_row, row, self.transformer) for merged_row in self.rows
        ):
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
                agreement=self.agreement,
                column_agreement=self.column_agreement,
                transformer=self.transformer,
            )
        )

    def build(self):
        return TableFragment(
            rows=[r for r in self.rows if not r.is_empty()], page=self.page
        )
