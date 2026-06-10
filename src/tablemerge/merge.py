import re
from collections.abc import Sequence
from itertools import zip_longest
from typing import Protocol
from unidecode import unidecode
from utils.column_values import normalize_column_value
from utils.column_names import normalize_column_name
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
from tablemerge.fragment_transformer import NullFragmentTransformer, FragmentTransformer
from tablemerge.fragments_compactor import FragmentsCompactor, NullFragmentsCompactor

MergeTarget = tuple[TableFragment, TablesFile]


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


_TITLE_ROW_RE = re.compile(r"^((figure|table|figura|tabla)\s+|fig\.\s*)\d+", re.IGNORECASE)


def is_title_row(row: Row) -> bool:
    non_empty = {col: val for col, val in row.get_columns().items() if not Row.is_empty_value(val)}
    if len(non_empty) != 1:
        return False
    val = next(iter(non_empty.values()))
    if isinstance(val, str):
        text = val.strip()
    else:
        texts = [v.value.strip() for v in val if v.value.strip()]
        text = texts[0] if texts else ""
    return bool(_TITLE_ROW_RE.match(text))


def filter_title_rows(tablesfile: TablesFile) -> TablesFile:
    filtered_tables = []
    for table in tablesfile.tables:
        filtered_fragments = []
        for fragment in table.get_table_fragments():
            head = [row for row in fragment.rows[:3] if not is_title_row(row)]
            filtered_fragments.append(
                TableFragment(rows=head + fragment.rows[3:], page=fragment.page)
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
                col for col in all_cols
                if not Row.is_semantic_column(col)
                and all(Row.is_empty_value(row.get_columns().get(col)) for row in fragment.rows)
            }
            new_rows = [
                Row(
                    agreement_level_=row.agreement_level_,
                    sources_=row.sources_,
                    **{k: v for k, v in row.get_columns().items() if k not in empty_cols},
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


def same_row(left: Row, right: Row) -> bool:
    # TODO compare using a broader similarity criteria
    left_columns = left.normalize().get_columns()
    right_columns = right.normalize().get_columns()
    return {k: transliterate_value(v) for k, v in left_columns.items()} == {
        k: transliterate_value(v) for k, v in right_columns.items()
    }


def merge_rows(
    left: Row,
    right: Row,
    agreement: Agreement = SimpleCountAgreement(),
    column_agreement: bool = False,
) -> Row:
    agreement_level = agreement.calculate_level(left, right)

    if column_agreement:
        columns = merge_columns_with_agreement(left, right)
    else:
        columns = merge_columns_without_agreement(left, right)

    left_sources = left.sources_ or []
    right_sources = right.sources_ or []
    sources = list(dict.fromkeys(left_sources + right_sources)) or None

    return Row(agreement_level_=agreement_level, sources_=sources, **columns)


def merge_columns_without_agreement(left: Row, right: Row):
    return {
        **right.normalize().get_columns(),
        **left.normalize().get_columns(),
    }


def merge_columns_with_agreement(left: Row, right: Row):
    column_values: dict[str, dict[str, int]] = {}
    for row in [left, right]:
        for column_name, column_value in row.normalize().get_columns().items():
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


def to_values_with_agreement(column_value: ColumnValue) -> list[ValueWithAgreement]:
    if column_value is None:
        return []
    if isinstance(column_value, str):
        return [ValueWithAgreement(value=column_value, agreement_level=1)]
    return column_value


def merge_tablesfiles(
    tablesfiles: list[TablesFile],
    agreement: Agreement = SimpleCountAgreement(),
    column_agreement=False,
    analyzers: list[Analyzer] = [],
    transformer: FragmentTransformer = NullFragmentTransformer(),
    compactor: FragmentsCompactor = NullFragmentsCompactor(),
) -> TablesFile:
    """
    Process one or more "tables" elements
    """
    if not tablesfiles:
        raise MergeError("Must pass at least TablesFile element")

    tablesfiles = [compactor.compact(tf) for tf in tablesfiles]

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
        fragments_clusters = make_fragments_clusters(
            tables_cluster, tablesfiles, transformer
        )

        for merge_targets in fragments_clusters.values():

            # =================================
            # Combine rows of the same fragment
            # =================================

            # TODO sort first so longest cluster is the first one
            left_fragment, left_tablesfile = merge_targets[0]
            if not left_fragment:
                raise MergeError(f"no left fragment in {merge_targets}")

            first_right = next((f for f, _ in merge_targets[1:] if f is not None), None)
            aligner = ColumnAligner(
                left_fragment,
                first_right,
                analyzers=analyzers,
            )
            left_fragment = TableFragment(
                rows=[aligner.rename_row(r) for r in left_fragment.rows],
                page=left_fragment.page,
            )

            table_fragment_builder = TableFragmentBuilder(
                left_fragment,
                left_tablesfile.uuid,
                agreement,
                column_agreement,
            )

            for right_fragment, right_tablesfile in merge_targets[1:]:
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
                        if same_row(left_row, right_rows[right_index]):
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
    citation = TablesFile.normalize_citation(tablesfiles[0].citation)

    return TablesFile(tables=merged_tables, citation=citation)


def normalize_fragment(
    fragment: TableFragment, transformer: FragmentTransformer
) -> TableFragment:
    return transformer.transform_fragment(fragment)


def make_fragments_clusters(
    tables_cluster: Sequence[Table | None],
    tablesfiles: Sequence[TablesFile],
    transformer: FragmentTransformer,
) -> dict[int, list[MergeTarget]]:
    fragments_clusters: dict[int, list[MergeTarget]] = {}
    for table, tablesfile in zip(tables_cluster, tablesfiles):
        if table is None:
            continue
        for fragment in table.get_table_fragments():
            fragments_clusters.setdefault(fragment.page, []).append(
                (normalize_fragment(fragment, transformer), tablesfile)
            )
    return fragments_clusters


class TableFragmentBuilder:
    rows: list[Row]
    page: int
    agreement: Agreement
    column_agreement: bool

    def __init__(
        self,
        initial_fragment: TableFragment,
        initial_uuid: str | None,
        agreement: Agreement,
        column_agreement: bool,
    ):
        self.agreement = agreement
        self.column_agreement = column_agreement
        self.page = initial_fragment.page
        do_agreement = agreement is not None
        self.rows = [
            row.model_copy(
                update={"sources_": [initial_uuid] if initial_uuid else None}
            )
            for row in map(
                lambda r: r.normalize(do_agreement),
                initial_fragment.rows,
            )
        ]

    def next_left_rows(self):
        rows = self.rows
        self.rows = []
        return list(rows)

    def _append(self, row: Row):
        new = row.normalize(self.agreement is not None)
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
                agreement=self.agreement,
                column_agreement=self.column_agreement,
            )
        )

    def build(self):
        return TableFragment(
            rows=[r for r in self.rows if not r.is_empty()], page=self.page
        )
