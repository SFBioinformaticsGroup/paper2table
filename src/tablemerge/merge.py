import re
from collections.abc import Sequence
from itertools import zip_longest
from typing import Protocol
from unidecode import unidecode
from utils.rows import is_empty_row
from tablevalidate.schema import (
    TablesFile,
    Table,
    TableFragment,
    TableWithFragments,
    ValueWithAgreement,
    ColumnValue,
    Row,
    get_table_fragments,
)


def filter_semantic_columns(tablesfile: TablesFile) -> TablesFile:
    filtered_tables = []
    for table in tablesfile.tables:
        filtered_fragments = []
        for fragment in get_table_fragments(table):
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


def normalize_str_value(value: str):
    return re.sub(r"\s+", " ", value.strip()).lower()


def normalize_value(value: ColumnValue) -> ColumnValue:
    if isinstance(value, str):
        return normalize_str_value(value)
    if isinstance(value, list):
        return [
            ValueWithAgreement(
                value=normalize_str_value(value_with_agreement.value),
                agreement_level=value_with_agreement.agreement_level,
            )
            for value_with_agreement in value
        ]
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


def extract_column_str_values(column_value: ColumnValue) -> list[str]:
    """Normalize + transliterate a ColumnValue into a flat list of strings."""
    if isinstance(column_value, str):
        return [unidecode(normalize_str_value(column_value))]
    return [unidecode(normalize_str_value(vwa.value)) for vwa in column_value]


def column_value_set(rows: list[Row], col: str) -> set[str]:
    """Collect normalized values of column `col` across all rows."""
    result: set[str] = set()
    for row in rows:
        val = row.get_columns().get(col)
        if val is not None:
            result.update(extract_column_str_values(val))
    return result


def jaccard(a: set[str], b: set[str]) -> float:
    """
    Jaccard similarity: |a ∩ b| / |a ∪ b|.
    Returns 0.0 when both sets are empty (no evidence to compare).
    Range: [0.0, 1.0]. 1.0 means identical value sets; 0.0 means no overlap.
    """
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def all_column_names(rows: list[Row]) -> list[str]:
    """Return ordered, deduplicated column names across all rows."""
    return list(dict.fromkeys(c for row in rows for c in row.get_columns()))


def find_column_mapping(
    left: TableFragment,
    right: TableFragment,
    threshold: float = 0.5,
    max_sample: int = 50,
) -> dict[str, str]:
    """
    Detect correspondences between numeric and semantic column names across two
    fragments, using Jaccard similarity on their normalized value sets.

    Returns a dict mapping numeric_col_name -> semantic_col_name. Only activates
    when one fragment has exclusively numeric column names and the other has
    exclusively semantic ones; returns {} otherwise (both numeric, both semantic,
    or mixed).

    Two columns are considered equivalent when their Jaccard index (size of value
    intersection / size of value union, after normalization) is >= threshold.
    Matching is one-to-one: the best-scoring pair is assigned first, then those
    columns are excluded from subsequent pairings (greedy descending order).

    Args:
        left: the "base" fragment (typically from the semantic reader).
        right: the fragment being merged in (typically from the numeric reader).
        threshold: minimum Jaccard similarity to consider two columns equivalent.
            0.0 maps everything; 1.0 requires identical value sets. Default 0.5
            tolerates up to half of the values being different (e.g. one table
            has extra rows the other doesn't).
        max_sample: number of rows sampled per fragment for efficiency.
    """
    left_rows = left.rows[:max_sample]
    right_rows = right.rows[:max_sample]
    if not left_rows or not right_rows:
        return {}

    left_cols = all_column_names(left_rows)
    right_cols = all_column_names(right_rows)

    left_numeric = [c for c in left_cols if not Row.is_semantic_column(c)]
    right_numeric = [c for c in right_cols if not Row.is_semantic_column(c)]
    left_semantic = [c for c in left_cols if Row.is_semantic_column(c)]
    right_semantic = [c for c in right_cols if Row.is_semantic_column(c)]

    if right_numeric and left_semantic and not left_numeric:
        numeric_cols, numeric_rows = right_numeric, right_rows
        semantic_cols, semantic_rows = left_semantic, left_rows
    elif left_numeric and right_semantic and not right_numeric:
        numeric_cols, numeric_rows = left_numeric, left_rows
        semantic_cols, semantic_rows = right_semantic, right_rows
    else:
        return {}

    num_sets = {c: column_value_set(numeric_rows, c) for c in numeric_cols}
    sem_sets = {c: column_value_set(semantic_rows, c) for c in semantic_cols}

    scores = [
        (jaccard(num_sets[nc], sem_sets[sc]), nc, sc)
        for nc in numeric_cols
        for sc in semantic_cols
        if jaccard(num_sets[nc], sem_sets[sc]) >= threshold
    ]
    scores.sort(key=lambda x: -x[0])

    mapping: dict[str, str] = {}
    used: set[str] = set()
    for _, nc, sc in scores:
        if nc not in mapping and sc not in used:
            mapping[nc] = sc
            used.add(sc)
    return mapping


def rename_row_columns(row: Row, mapping: dict[str, str]) -> Row:
    if not mapping:
        return row
    return Row(
        agreement_level_=row.agreement_level_,
        sources_=row.sources_,
        **{mapping.get(k, k): v for k, v in row.get_columns().items()},
    )


def rename_fragment_columns(fragment: TableFragment, mapping: dict[str, str]) -> TableFragment:
    if not mapping:
        return fragment
    return TableFragment(
        rows=[rename_row_columns(r, mapping) for r in fragment.rows],
        page=fragment.page,
    )


def same_row(left: Row, right: Row) -> bool:
    # TODO compare using a broader similarity criteria
    left_cols = normalize_row(left).get_columns()
    right_cols = normalize_row(right).get_columns()
    return {k: transliterate_value(v) for k, v in left_cols.items()} == {
        k: transliterate_value(v) for k, v in right_cols.items()
    }


def merge_rows(
    left: Row,
    right: Row,
    agreement: Agreement = SimpleCountAgreement(),
    column_agreement=False,
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
        **normalize_row(right).get_columns(),
        **normalize_row(left).get_columns(),
    }


def merge_columns_with_agreement(left: Row, right: Row):
    column_values: dict[str, dict[str, int]] = {}
    for row in [left, right]:
        for column_name, column_value in normalize_row(row).get_columns().items():
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

            first_right = next((f for f in fragments_cluster[1:] if f is not None), None)
            if first_right is not None:
                left_mapping = find_column_mapping(left_fragment, first_right)
                left_col_names = set(all_column_names(left_fragment.rows[:1]))
                if left_mapping and left_col_names & set(left_mapping.keys()):
                    left_fragment = rename_fragment_columns(left_fragment, left_mapping)

            table_fragment_builder = TableFragmentBuilder(
                left_fragment, tablesfiles[0].uuid, agreement, column_agreement
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
                right_rows = right_fragment.rows
                left_for_align = TableFragment(rows=table_fragment_builder.rows, page=right_fragment.page)
                right_mapping = find_column_mapping(left_for_align, right_fragment)
                right_col_names = set(all_column_names(right_fragment.rows[:1]))
                if right_mapping and right_col_names & set(right_mapping.keys()):
                    right_rows = [rename_row_columns(r, right_mapping) for r in right_rows]
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
    citation = tablesfiles[0].citation

    return TablesFile(tables=merged_tables, citation=citation)


def make_fragments_clusters(tables_cluster: Sequence[Table | None]):
    fragments_clusters: dict[int, list[TableFragment]] = {}
    for table in tables_cluster:
        if table is None:
            continue
        for fragment in get_table_fragments(table):
            fragments_clusters.setdefault(fragment.page, []).append(fragment)
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
                lambda r: normalize_row(r, do_agreement), initial_fragment.rows
            )
        ]

    def next_left_rows(self):
        rows = self.rows
        self.rows = []
        return list(rows)

    def _append(self, row: Row):
        new = normalize_row(row, self.agreement is not None)
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
            rows=[r for r in self.rows if not is_empty_row(r)], page=self.page
        )
