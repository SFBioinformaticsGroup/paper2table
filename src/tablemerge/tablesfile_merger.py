from collections.abc import Sequence
from dataclasses import dataclass
from itertools import zip_longest
from unidecode import unidecode

from tablevalidate.schema import (
    TablesFile,
    Table,
    TableFragment,
    TableWithFragments,
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
            fragments_clusters.setdefault(FragmentClusterKey(adjusted_page, position), []).append(
                (fragment, tablesfile)
            )
    return fragments_clusters


class TablesFileMerger:
    def __init__(
        self,
        agreement: Agreement = SimpleCountAgreement(),
        column_agreement: bool = False,
        analyzers: list[MergeTimeAnalyzer] = [],
    ):
        self.agreement = agreement
        self.column_agreement = column_agreement
        self.analyzers = analyzers

    def merge(self, tablesfiles: list[TablesFile], page_offsets: list[int] | None = None) -> TablesFile:
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

        merged_tables: list[Table] = []

        tables_clusters = list(zip_longest(*map(lambda t: t.tables, tablesfiles)))
        for tables_cluster in tables_clusters:
            merged_fragments: list[TableFragment] = []
            fragments_clusters = make_fragments_clusters(tables_cluster, tablesfiles, page_offsets)

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

                table_fragment_builder = TableFragmentBuilder(
                    left_fragment,
                    left_tablesfile.uuid,
                    self.agreement,
                    self.column_agreement,
                )

                for right_fragment, right_tablesfile in merge_targets[1:]:
                    if not right_fragment:
                        break

                    right_uuid = right_tablesfile.uuid
                    right_rows = [
                        merge_aligner.rename_row(r).model_copy(update={"row_": i})
                        for i, r in enumerate(right_fragment.rows)
                    ]
                    left_rows = table_fragment_builder.next_left_rows()
                    right_idx = 0

                    for left_row in left_rows:
                        while right_idx < len(right_rows) and (
                            right_rows[right_idx].row_ or 0
                        ) < (left_row.row_ or 0):
                            table_fragment_builder.append_skipped(
                                [right_rows[right_idx]], right_uuid
                            )
                            right_idx += 1

                        if (
                            right_idx < len(right_rows)
                            and right_rows[right_idx].row_ == left_row.row_
                            and same_row(left_row, right_rows[right_idx])
                        ):
                            right_row = right_rows[right_idx].model_copy(
                                update={
                                    "sources_": [right_uuid] if right_uuid else None
                                }
                            )
                            table_fragment_builder.merge_and_append(left_row, right_row)
                            right_idx += 1
                        else:
                            table_fragment_builder.append_unmatched(left_row)

                    table_fragment_builder.append_skipped(
                        right_rows[right_idx:], right_uuid
                    )

                merged_fragments.append(table_fragment_builder.build())

            merged_tables.append(TableWithFragments(table_fragments=merged_fragments))

        # # TODO pick all citations
        citation = TablesFile.normalize_citation(tablesfiles[0].citation)

        return TablesFile(tables=merged_tables, citation=citation)


def merge_tablesfiles(
    tablesfiles: list[TablesFile],
    agreement: Agreement = SimpleCountAgreement(),
    column_agreement: bool = False,
    analyzers: list[MergeTimeAnalyzer] = [],
    page_offsets: list[int] | None = None,
) -> TablesFile:
    return TablesFileMerger(
        agreement=agreement,
        column_agreement=column_agreement,
        analyzers=analyzers,
    ).merge(tablesfiles, page_offsets=page_offsets)
