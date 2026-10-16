from collections.abc import Sequence
from dataclasses import dataclass
from itertools import zip_longest
from typing import Dict, List, cast
from unidecode import unidecode

from tablevalidate.schema import (
    TablesFile,
    Table,
    TableFragment,
    TableWithFragments,
    TableWithRows,
    ValueWithAgreement,
    ColumnValue,
    Row,
)
from tablemerge.columns_aligner import MergeTimeColumnAligner
from tablemerge.analyzers import MergeTimeAnalyzer
from tablemerge.agreement import Agreement, SimpleCountAgreement
from tablemerge.errors import MergeError
from tablemerge.fragments_builder import TableFragmentBuilder

MergeTarget = tuple[TableFragment, TablesFile]

from Levenshtein import ratio


@dataclass(frozen=True, order=True)
class FragmentClusterKey:
    """Key for grouping fragments to merge.

    Two fragments from the same paper on the same page get different positions,
    so they land in separate clusters and are never merged with each other.
    """

    page: int
    position: int


def transliterate_value(value: ColumnValue) -> ColumnValue:
    if isinstance(value, str):
        return transliterate_scalar(value)
    if isinstance(value, list):
        return transliterate_multivalued(value)
    return value


def transliterate_scalar(value: str):
    return unidecode(value)


def transliterate_multivalued(value: List[ValueWithAgreement]):
    return [
        ValueWithAgreement(value=unidecode(v.value), agreement_level=v.agreement_level)
        for v in value
    ]


def same_row(left: Row, right: Row) -> bool:
    left_columns = left.normalize().get_columns()
    right_columns = right.normalize().get_columns()

    sorted_column_keys = sorted(left_columns.keys())

    return (
        ratio(
            get_text(left_columns, sorted_column_keys),
            get_text(right_columns, sorted_column_keys),
        )
        > 0.6
    )

def get_text(columns: Dict[str, ColumnValue], sorted_column_keys: list[str]):
    # TODO we could also zip columns and try different combinations
    return "".join(
        transliterate_scalar(get_scalar(columns.get(k, "")))
        for k in sorted_column_keys
    )


def get_scalar(value: ColumnValue):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return value[0].value
    return ""


def make_fragments_clusters(
    tables_cluster: Sequence[Table | None],
    tablesfiles: Sequence[TablesFile],
    page_offsets: Sequence[int],
) -> dict[FragmentClusterKey, list[MergeTarget]]:
    fragments_clusters: dict[FragmentClusterKey, list[MergeTarget]] = {}
    for table, tablesfile, offset in zip(tables_cluster, tablesfiles, page_offsets):
        if table is None:
            continue
        page_counts: dict[int, int] = {}
        for fragment in table.get_table_fragments():
            adjusted_page = fragment.page + offset
            position = page_counts.get(adjusted_page, 0)
            page_counts[adjusted_page] = position + 1
            fragments_clusters.setdefault(
                FragmentClusterKey(adjusted_page, position), []
            ).append((fragment, tablesfile))
    return fragments_clusters


class TablesFileMerger:
    def __init__(
        self,
        agreement: Agreement = SimpleCountAgreement(),
        multivalued: bool = False,
        analyzers: list[MergeTimeAnalyzer] = [],
    ):
        self.agreement = agreement
        self.multivalued = multivalued
        self.analyzers = analyzers

    def merge_fragment(
        self,
        builder: TableFragmentBuilder,
        left_rows: list[Row],
        right_rows: list[Row],
        right_source: str | None,
    ):
        """
        Merges rows from two different fragments
        This algorithm will try to pair each left row with each right row,
        preserving relative order.

        This algorithm grants that every row from both lists are
        included in final result.

        It uses a TableFragmentBuilder in order to accumulate results.
        """
        left_idx = 0
        right_idx = 0

        while left_idx < len(left_rows):
            tmp_right_idx = right_idx
            found = False
            while tmp_right_idx < len(right_rows) and not found:
                if same_row(left_rows[left_idx], right_rows[tmp_right_idx]):
                    found = True
                else:
                    tmp_right_idx += 1

            if found:
                builder.append_from_right(
                    right_rows[right_idx:tmp_right_idx], right_source
                )
                builder.append_from_both(
                    left_rows[left_idx], right_rows[tmp_right_idx], right_source
                )
                right_idx = tmp_right_idx + 1
            else:
                builder.append_from_left(left_rows[left_idx])

            left_idx += 1

        builder.append_from_right(right_rows[right_idx:], right_source)

    def merge(
        self, tablesfiles: list[TablesFile], page_offsets: list[int] | None = None
    ) -> TablesFile:
        """Merge multiple TablesFiles into one.

        Two-level pairing: tables by index (zip_longest pairs table N across all papers),
        then fragments by adjusted page number within each table pair. Fragments sharing a
        page are merged together; fragments whose page has no counterpart in any other paper
        are output as-is with agreement level 1.
        """
        if not tablesfiles:
            raise MergeError("Must pass at least TablesFile element")

        if page_offsets is None:
            page_offsets = [0] * len(tablesfiles)

        merged_tables: list[TableWithRows | TableWithFragments] = []

        tables_clusters = list(zip_longest(*map(lambda t: t.tables, tablesfiles)))
        for tables_cluster in tables_clusters:
            merged_fragments: list[TableFragment] = []
            fragments_clusters = make_fragments_clusters(
                tables_cluster, tablesfiles, page_offsets
            )

            for _page, merge_targets in sorted(fragments_clusters.items()):
                # TODO sort first so longest cluster is the first one
                left_fragment, left_tablesfile = merge_targets[0]
                if not left_fragment:
                    raise MergeError(f"no left fragment in {merge_targets}")

                first_right = next(
                    (f for f, _ in merge_targets[1:] if f is not None), None
                )
                merge_aligner = MergeTimeColumnAligner(
                    left_fragment, first_right, self.analyzers
                )

                left_fragment = TableFragment(
                    rows=[merge_aligner.rename_row(r) for r in left_fragment.rows],
                    page=left_fragment.page,
                )

                calculate_agreement = self.agreement is not None
                table_fragment_builder = TableFragmentBuilder(
                    initial_rows=(
                        row.normalize(calculate_agreement) for row in left_fragment.rows
                    ),
                    initial_uuid=left_tablesfile.uuid,
                    page=left_fragment.page,
                    agreement=self.agreement,
                    multivalued=self.multivalued,
                )

                for right_fragment, right_tablesfile in merge_targets[1:]:
                    if not right_fragment:
                        break

                    right_rows = [
                        merge_aligner.rename_row(row.normalize(calculate_agreement))
                        for row in right_fragment.rows
                    ]
                    left_rows = table_fragment_builder.prepare_next_left_rows()
                    self.merge_fragment(
                        table_fragment_builder,
                        left_rows,
                        right_rows,
                        right_tablesfile.uuid,
                    )

                merged_fragments.append(table_fragment_builder.build())

            merged_tables.append(TableWithFragments(table_fragments=merged_fragments))

        # # TODO pick all citations
        citation = TablesFile.normalize_citation(tablesfiles[0].citation)

        return TablesFile(tables=merged_tables, citation=citation)


def merge_tablesfiles(
    tablesfiles: list[TablesFile],
    agreement: Agreement = SimpleCountAgreement(),
    multivalued: bool = False,
    analyzers: list[MergeTimeAnalyzer] = [],
    page_offsets: list[int] | None = None,
) -> TablesFile:
    return TablesFileMerger(
        agreement=agreement,
        multivalued=multivalued,
        analyzers=analyzers,
    ).merge(tablesfiles, page_offsets=page_offsets)
