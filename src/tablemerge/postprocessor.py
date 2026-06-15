from typing import Any, Protocol

from tablevalidate.schema import (
    TablesFile,
    TableFragment,
    TableWithFragments,
    Row,
    ValueWithAgreement,
    ColumnValue,
)
from utils.coerce import coerce_str
from .merge import drop_empty_non_semantic_columns, drop_empty_tables, filter_semantic_columns
from .schema import Schema


class PostProcessor(Protocol):
    @property
    def settings(self) -> dict: ...
    def postprocess(self, tablesfile: TablesFile) -> TablesFile: ...


class FilterSemanticColumnsPostProcessor:
    @property
    def settings(self) -> dict:
        return {}

    def postprocess(self, tablesfile: TablesFile) -> TablesFile:
        return filter_semantic_columns(tablesfile)


class DropEmptyNonSemanticColumnsPostProcessor:
    @property
    def settings(self) -> dict:
        return {}

    def postprocess(self, tablesfile: TablesFile) -> TablesFile:
        return drop_empty_non_semantic_columns(tablesfile)


class DropEmptyTablesPostProcessor:
    @property
    def settings(self) -> dict:
        return {}

    def postprocess(self, tablesfile: TablesFile) -> TablesFile:
        return drop_empty_tables(tablesfile)


class SchemaPostProcessor:
    def __init__(
        self,
        schema: Schema,
        filter_columns: bool = False,
        order_columns: bool = False,
        coerce_types: bool = False,
    ):
        self.schema = schema
        self.filter_columns = filter_columns
        self.order_columns = order_columns
        self.coerce_types = coerce_types

    @property
    def settings(self) -> dict:
        return {
            "filter_schema_columns": self.filter_columns,
            "order_schema_columns": self.order_columns,
            "coerce_schema_column_types": self.coerce_types,
        }

    def postprocess(self, tablesfile: TablesFile) -> TablesFile:
        if self.filter_columns:
            tablesfile = self._filter_schema_columns(tablesfile)
        if self.order_columns:
            tablesfile = self._order_schema_columns(tablesfile)
        if self.coerce_types:
            tablesfile = self._coerce_schema_column_types(tablesfile)
        return tablesfile

    def _rebuild_tablesfile(self, tablesfile: TablesFile, tables: list) -> TablesFile:
        return TablesFile(
            tables=tables,
            citation=tablesfile.citation,
            metadata=tablesfile.metadata,
            uuid=tablesfile.uuid,
        )

    def _table_column_names(self, table) -> set[str]:
        return {
            col
            for fragment in table.get_table_fragments()
            for row in fragment.rows
            for col in row.get_columns()
        }

    def _filter_schema_columns(self, tablesfile: TablesFile) -> TablesFile:
        schema_keys = self.schema.keys()
        kept = [t for t in tablesfile.tables if schema_keys & self._table_column_names(t)]
        return self._rebuild_tablesfile(tablesfile, kept)

    def _order_schema_columns(self, tablesfile: TablesFile) -> TablesFile:
        schema_keys = list(self.schema.keys())

        def reorder_row(row: Row) -> Row:
            cols = row.get_columns()
            ordered = {k: cols[k] for k in schema_keys if k in cols}
            ordered |= {k: v for k, v in cols.items() if k not in ordered}
            return Row(agreement_level_=row.agreement_level_, sources_=row.sources_, row_=row.row_, **ordered)

        def reorder_fragment(fragment: TableFragment) -> TableFragment:
            return TableFragment(rows=list(map(reorder_row, fragment.rows)), page=fragment.page)

        tables = [
            TableWithFragments(table_fragments=list(map(reorder_fragment, t.get_table_fragments())))
            for t in tablesfile.tables
        ]
        return self._rebuild_tablesfile(tablesfile, tables)

    def _coerce_schema_column_types(self, tablesfile: TablesFile) -> TablesFile:
        def coerce_column_value(value: ColumnValue, target_type: type) -> ColumnValue:
            if value is None:
                return None
            if isinstance(value, str):
                return coerce_str(value, target_type)
            return [
                ValueWithAgreement(
                    value=coerce_str(v.value, target_type),
                    agreement_level=v.agreement_level,
                )
                for v in value
            ]

        def coerce_row(row: Row) -> Row:
            cols = {
                col: (
                    coerce_column_value(val, self.schema[col][0])
                    if col in self.schema
                    else val
                )
                for col, val in row.get_columns().items()
            }
            return Row(agreement_level_=row.agreement_level_, sources_=row.sources_, row_=row.row_, **cols)

        def coerce_fragment(fragment: TableFragment) -> TableFragment:
            return TableFragment(rows=list(map(coerce_row, fragment.rows)), page=fragment.page)

        tables = [
            TableWithFragments(table_fragments=list(map(coerce_fragment, t.get_table_fragments())))
            for t in tablesfile.tables
        ]
        return self._rebuild_tablesfile(tablesfile, tables)


def build_postprocessors(
    schema: Schema,
    filter_columns: bool,
    order_columns: bool,
    coerce_types: bool,
    only_semantic_columns: bool = False,
    drop_empty_non_semantic_columns: bool = True,
    drop_empty_tables: bool = True,
) -> list[PostProcessor]:
    result: list[PostProcessor] = []
    if only_semantic_columns:
        result.append(FilterSemanticColumnsPostProcessor())
    if drop_empty_non_semantic_columns:
        result.append(DropEmptyNonSemanticColumnsPostProcessor())
    if drop_empty_tables:
        result.append(DropEmptyTablesPostProcessor())
    if schema:
        result.append(SchemaPostProcessor(schema, filter_columns, order_columns, coerce_types))
    return result
