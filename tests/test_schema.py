# pyright: reportCallIssue=false
from tablemerge.postprocessor import (
    SchemaPostProcessor,
    DropEmptyNonSemanticColumnsPostProcessor,
    DropEmptyTablesPostProcessor,
)
from utils.column_schema import ColumnSchema
from tablevalidate.schema import (
    TablesFile,
    TableWithFragments,
    TableFragment,
    Row,
    ValueWithAgreement,
)


def wrap(rows: list[Row], page=1, citation="") -> TablesFile:
    return TablesFile(
        tables=[
            TableWithFragments(table_fragments=[TableFragment(rows=rows, page=page)])
        ],
        citation=citation,
    )


def wrap_two_tables(rows1: list[Row], rows2: list[Row], citation="") -> TablesFile:
    return TablesFile(
        tables=[
            TableWithFragments(table_fragments=[TableFragment(rows=rows1, page=1)]),
            TableWithFragments(table_fragments=[TableFragment(rows=rows2, page=2)]),
        ],
        citation=citation,
    )


def rows_of(tf: TablesFile, table=0, fragment=0):
    return tf.tables[table].get_table_fragments()[fragment].rows


FILTER_SCHEMA = ColumnSchema({"name": str, "species": str})


def filter_processor() -> SchemaPostProcessor:
    return SchemaPostProcessor(FILTER_SCHEMA, filter_columns=True)


def test_filter_keeps_table_with_matching_column():
    result = filter_processor().postprocess(wrap([Row(name="foo")]))
    assert len(result.tables) == 1


def test_filter_drops_table_with_no_matching_column():
    result = filter_processor().postprocess(wrap([Row(color="red", size="big")]))
    assert len(result.tables) == 0


def test_filter_keeps_table_with_partial_match():
    result = filter_processor().postprocess(
        wrap([Row(species="Canis lupus", habitat="forest")])
    )
    assert len(result.tables) == 1


def test_filter_mixed_tables():
    tf = wrap_two_tables([Row(name="Rosa")], [Row(color="red")])
    result = filter_processor().postprocess(tf)
    assert len(result.tables) == 1


def test_filter_preserves_citation():
    result = filter_processor().postprocess(
        wrap([Row(name="x")], citation="some citation")
    )
    assert result.citation == "some citation"


def test_filter_all_tables_dropped_returns_empty():
    tf = wrap_two_tables([Row(color="red")], [Row(size="big")])
    result = filter_processor().postprocess(tf)
    assert result.tables == []


_ORDER_SCHEMA = ColumnSchema({"name": str, "species": str, "family": str})


def order_processor() -> SchemaPostProcessor:
    return SchemaPostProcessor(_ORDER_SCHEMA, order_columns=True)


def test_order_schema_columns_come_first():
    result = order_processor().postprocess(
        wrap([Row(habitat="forest", name="Rosa", family="Rosaceae")])
    )
    cols = list(rows_of(result)[0].get_columns().keys())
    assert cols.index("name") < cols.index("habitat")
    assert cols.index("family") < cols.index("habitat")


def test_order_schema_order_respected():
    result = order_processor().postprocess(
        wrap([Row(family="Rosaceae", species="Rosa canina", name="Dog rose")])
    )
    cols = list(rows_of(result)[0].get_columns().keys())
    assert cols[:3] == ["name", "species", "family"]


def test_order_missing_schema_columns_not_inserted():
    result = order_processor().postprocess(wrap([Row(name="Rosa")]))
    cols = list(rows_of(result)[0].get_columns().keys())
    assert cols == ["name"]


def test_order_preserves_metadata():
    result = order_processor().postprocess(
        wrap([Row(name="Rosa", agreement_level_=3, sources_=["uuid1"])])
    )
    row = rows_of(result)[0]
    assert row.agreement_level_ == 3
    assert row.sources_ == ["uuid1"]


def test_order_preserves_row_number():
    result = order_processor().postprocess(wrap([Row(name="Rosa", row_=7)]))
    assert rows_of(result)[0].row_ == 7


COERCE_SCHEMA = ColumnSchema(
    {"year": int, "length": float, "active": bool, "label": str}
)


def coerce_processor() -> SchemaPostProcessor:
    return SchemaPostProcessor(COERCE_SCHEMA, coerce_types=True)


def coerce_cols(tf: TablesFile) -> dict:
    return rows_of(tf)[0].get_columns()


def test_coerce_types_int():
    assert (
        coerce_cols(coerce_processor().postprocess(wrap([Row(year="2020.0")])))["year"]
        == "2020"
    )


def test_coerce_types_float():
    assert (
        coerce_cols(coerce_processor().postprocess(wrap([Row(length="3")])))["length"]
        == "3.0"
    )


def test_coerce_types_bool_true():
    assert (
        coerce_cols(coerce_processor().postprocess(wrap([Row(active="yes")])))["active"]
        == "True"
    )


def test_coerce_types_bool_false():
    assert (
        coerce_cols(coerce_processor().postprocess(wrap([Row(active="no")])))["active"]
        == "False"
    )


def test_coerce_types_str_is_noop():
    assert (
        coerce_cols(coerce_processor().postprocess(wrap([Row(label="hello")])))["label"]
        == "hello"
    )


def test_coerce_types_unconvertible_left_unchanged():
    assert (
        coerce_cols(coerce_processor().postprocess(wrap([Row(year="N/A")])))["year"]
        == "N/A"
    )


def test_coerce_types_non_schema_column_untouched():
    assert (
        coerce_cols(coerce_processor().postprocess(wrap([Row(color="red")])))["color"]
        == "red"
    )


def test_coerce_preserves_row_number():
    result = coerce_processor().postprocess(wrap([Row(year="2020", row_=3)]))
    assert rows_of(result)[0].row_ == 3


def test_coerce_types_value_with_agreement():
    tf = wrap(
        [
            Row(
                year=[
                    ValueWithAgreement(value="2020.0", agreement_level=2),
                    ValueWithAgreement(value="bad", agreement_level=1),
                ]
            )
        ]
    )
    values = coerce_cols(coerce_processor().postprocess(tf))["year"]
    assert isinstance(values, list)
    assert values[0].value == "2020"
    assert values[1].value == "bad"
    assert values[0].agreement_level == 2


def test_coerce_types_preserves_metadata():
    result = coerce_processor().postprocess(
        wrap([Row(year="2020", agreement_level_=2, sources_=["u1"])])
    )
    row = rows_of(result)[0]
    assert row.agreement_level_ == 2
    assert row.sources_ == ["u1"]


def test_coerce_types_none_column_value_left_unchanged():
    assert (
        coerce_cols(coerce_processor().postprocess(wrap([Row(**{"year": None})])))[
            "year"
        ]
        is None
    )


def test_drop_empty_non_semantic_columns_postprocessor_removes_all_null_column():
    tablesfile = wrap(
        [
            Row(**{"0": None, "family": "Apiaceae"}),
            Row(**{"0": None, "family": "Fabaceae"}),
        ]
    )
    result = DropEmptyNonSemanticColumnsPostProcessor().postprocess(tablesfile)
    rows = result.tables[0].get_table_fragments()[0].rows
    assert rows == [
        Row(family="Apiaceae"),
        Row(family="Fabaceae"),
    ]


def test_drop_empty_tables_postprocessor_removes_empty_table():
    tablesfile = TablesFile(
        tables=[
            TableWithFragments(
                table_fragments=[TableFragment(rows=[Row(family="Apiaceae")], page=1)]
            ),
            TableWithFragments(
                table_fragments=[TableFragment(rows=[Row(family="")], page=2)]
            ),
        ],
        citation="",
    )
    result = DropEmptyTablesPostProcessor().postprocess(tablesfile)
    assert len(result.tables) == 1
    assert result.tables[0].get_table_fragments()[0].rows == [Row(family="Apiaceae")]
