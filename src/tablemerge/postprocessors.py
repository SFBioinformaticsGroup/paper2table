from tablevalidate.schema import TablesFile
from .schema import PostProcessor, Schema, SchemaPostProcessor
from .merge import drop_empty_non_semantic_columns, drop_empty_tables


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


def build_postprocessors(
    schema: Schema,
    filter_columns: bool,
    order_columns: bool,
    coerce_types: bool,
    drop_empty_non_semantic_columns: bool = True,
    drop_empty_tables: bool = True,
) -> list[PostProcessor]:
    result: list[PostProcessor] = []
    if drop_empty_non_semantic_columns:
        result.append(DropEmptyNonSemanticColumnsPostProcessor())
    if drop_empty_tables:
        result.append(DropEmptyTablesPostProcessor())
    if schema:
        result.append(SchemaPostProcessor(schema, filter_columns, order_columns, coerce_types))
    return result
