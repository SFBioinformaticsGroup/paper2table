from collections.abc import Sequence
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
from tablemerge.columns_aligner import ColumnAligner
from tablemerge.analyzers import Analyzer
from tablemerge.fragment_transformer import NullFragmentTransformer, FragmentTransformer
from tablemerge.fragments_compactor import FragmentsCompactor, NullFragmentsCompactor
from tablemerge.agreement import Agreement, SimpleCountAgreement
from tablemerge.errors import MergeError
from tablemerge.fragments_builder import TableFragmentBuilder

MergeTarget = tuple[TableFragment, TablesFile]


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


class TablesFileMerger:
    def __init__(
        self,
        agreement: Agreement = SimpleCountAgreement(),
        column_agreement: bool = False,
        analyzers: list[Analyzer] = [],
        transformer: FragmentTransformer = NullFragmentTransformer(),
        compactor: FragmentsCompactor = NullFragmentsCompactor(),
    ):
        self.agreement = agreement
        self.column_agreement = column_agreement
        self.analyzers = analyzers
        self.transformer = transformer
        self.compactor = compactor

    def merge(self, tablesfiles: list[TablesFile]) -> TablesFile:
        if not tablesfiles:
            raise MergeError("Must pass at least TablesFile element")

        tablesfiles = [self.compactor.compact(tf) for tf in tablesfiles]

        merged_tables: list[Table] = []

        tables_clusters = list(zip_longest(*map(lambda t: t.tables, tablesfiles)))
        for tables_cluster in tables_clusters:
            merged_fragments: list[TableFragment] = []
            fragments_clusters = make_fragments_clusters(
                tables_cluster, tablesfiles, self.transformer
            )

            for merge_targets in fragments_clusters.values():
                # TODO sort first so longest cluster is the first one
                left_fragment, left_tablesfile = merge_targets[0]
                if not left_fragment:
                    raise MergeError(f"no left fragment in {merge_targets}")

                first_right = next(
                    (f for f, _ in merge_targets[1:] if f is not None), None
                )
                aligner = ColumnAligner(
                    left_fragment,
                    first_right,
                    analyzers=self.analyzers,
                )
                left_fragment = TableFragment(
                    rows=[aligner.rename_row(r) for r in left_fragment.rows],
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

                    if left_fragment.page != right_fragment.page:
                        raise MergeError(
                            f"Pages don't match: {left_fragment.page} != {right_fragment.page}"
                        )

                    right_uuid = right_tablesfile.uuid
                    right_rows = [
                        aligner.rename_row(r).model_copy(update={"row_": i})
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
    analyzers: list[Analyzer] = [],
    transformer: FragmentTransformer = NullFragmentTransformer(),
    compactor: FragmentsCompactor = NullFragmentsCompactor(),
) -> TablesFile:
    return TablesFileMerger(
        agreement=agreement,
        column_agreement=column_agreement,
        analyzers=analyzers,
        transformer=transformer,
        compactor=compactor,
    ).merge(tablesfiles)
