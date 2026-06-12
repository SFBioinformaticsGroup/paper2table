from typing import Protocol

from tablevalidate.schema import (
    Table,
    TableFragment,
    TableWithFragments,
    TablesFile,
    Row,
)


class FragmentsCompactor(Protocol):
    @property
    def settings(self) -> dict: ...

    def compact(self, tablesfile: TablesFile) -> TablesFile: ...


class NullFragmentsCompactor:
    @property
    def settings(self) -> dict:
        return {}

    def compact(self, tablesfile: TablesFile) -> TablesFile:
        return tablesfile


class ConsecutiveFragmentsCompactor:
    def non_semantic_columns_match(
        self, one: TableFragment, other: TableFragment
    ) -> bool:
        raise NotImplementedError

    def semantic_fragments_are_close(
        self, one: TableFragment, other: TableFragment
    ) -> bool:
        raise NotImplementedError

    def all_semantic_columns(self, fragment: TableFragment) -> bool:
        return all(Row.is_semantic_column(name) for name in fragment.get_column_names())

    def columns_match(self, one: TableFragment, other: TableFragment) -> bool:
        if not one.get_column_names() or not other.get_column_names():
            return True
        if self.all_semantic_columns(one) and self.all_semantic_columns(other):
            return (
                self.semantic_fragments_are_close(one, other)
                and one.get_column_names() == other.get_column_names()
            )
        return self.non_semantic_columns_match(one, other)

    def can_merge_with_table(self, table: Table, other: TableFragment) -> bool:
        previous_fragments = table.get_table_fragments()
        if not previous_fragments:
            return False
        previous_fragment = previous_fragments[-1]
        return self.columns_match(previous_fragment, other)

    def compact(self, tablesfile: TablesFile) -> TablesFile:
        compacted: list[Table] = []
        for table in tablesfile.tables:
            fragments = table.get_table_fragments()
            if (
                fragments
                and compacted
                and self.can_merge_with_table(compacted[-1], fragments[0])
            ):
                prev_fragments = compacted[-1].get_table_fragments()
                last = prev_fragments[-1]
                merged = TableFragment(rows=last.rows + fragments[0].rows, page=fragments[0].page)
                compacted[-1] = TableWithFragments(
                    table_fragments=prev_fragments[:-1] + [merged]
                )
            else:
                compacted.append(table)
        return TablesFile(
            tables=compacted,
            citation=tablesfile.citation,
            metadata=tablesfile.metadata,
            uuid=tablesfile.uuid,
        )


class SafeConsecutiveFragmentsCompactor(ConsecutiveFragmentsCompactor):
    @property
    def settings(self) -> dict:
        return {"mode": "safe"}

    def non_semantic_columns_match(
        self, one: TableFragment, other: TableFragment
    ) -> bool:
        return False

    def semantic_fragments_are_close(
        self, one: TableFragment, other: TableFragment
    ) -> bool:
        return one.page <= other.page <= one.page + 1


class UnsafeConsecutiveFragmentsCompactor(ConsecutiveFragmentsCompactor):
    @property
    def settings(self) -> dict:
        return {"mode": "unsafe"}

    def semantic_fragments_are_close(
        self, one: TableFragment, other: TableFragment
    ) -> bool:
        return True

    def non_semantic_columns_match(
        self, one: TableFragment, other: TableFragment
    ) -> bool:
        return one.columns_count() == other.columns_count()
