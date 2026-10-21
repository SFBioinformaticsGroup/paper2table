# pyright: reportCallIssue=false
from utils.postprocessor import (
    SchemaPostProcessor,
    DropEmptyColumnsPostProcessor,
    DropEmptyTablesPostProcessor,
)
from utils.column_schema import ColumnSchema
from tablevalidate.schema import (
    TablesFile,
    Table,
    TableWithFragments,
    TableFragment,
    Metadata,
    Curation,
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
    assert rows_of(result) == [Row(name="foo")]


def test_filter_drops_table_with_no_matching_column():
    result = filter_processor().postprocess(wrap([Row(color="red", size="big")]))
    assert result.tables == []


def test_filter_removes_non_schema_semantic_columns():
    result = filter_processor().postprocess(
        wrap([Row(species="Canis lupus", habitat="forest")])
    )
    assert rows_of(result) == [Row(species="Canis lupus")]


def test_filter_mixed_tables():
    tf = wrap_two_tables([Row(name="Rosa")], [Row(color="red")])
    result = filter_processor().postprocess(tf)
    assert rows_of(result) == [Row(name="Rosa")]


def test_filter_preserves_non_semantic_columns():
    result = filter_processor().postprocess(
        wrap([Row(name="Rosa", **{"1": "a", "2": "b"})])
    )
    assert rows_of(result) == [Row(name="Rosa", **{"1": "a", "2": "b"})]


def test_filter_preserves_table_with_only_non_semantic_columns():
    result = filter_processor().postprocess(wrap([Row(**{"1": "a", "2": "b"})]))
    assert rows_of(result) == [Row(**{"1": "a", "2": "b"})]


def test_filter_drops_semantic_non_schema_leaves_non_semantic():
    result = filter_processor().postprocess(
        wrap([Row(habitat="forest", **{"1": "a"})])
    )
    assert rows_of(result) == [Row(**{"1": "a"})]


def test_filter_all_three_column_types():
    result = filter_processor().postprocess(
        wrap([Row(name="Rosa", habitat="forest", **{"1": "a"})])
    )
    assert rows_of(result) == [Row(name="Rosa", **{"1": "a"})]


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
        == 2020
    )


def test_coerce_types_float():
    assert (
        coerce_cols(coerce_processor().postprocess(wrap([Row(length="3")])))["length"]
        == 3.0
    )


def test_coerce_types_bool_true():
    assert (
        coerce_cols(coerce_processor().postprocess(wrap([Row(active="yes")])))["active"]
        is True
    )


def test_coerce_types_bool_false():
    assert (
        coerce_cols(coerce_processor().postprocess(wrap([Row(active="no")])))["active"]
        is False
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
    assert values[0].value == 2020
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


def test_drop_empty_columns_postprocessor_removes_all_null_column():
    tablesfile = wrap(
        [
            Row(**{"0": None, "family": "Apiaceae"}),
            Row(**{"0": None, "family": "Fabaceae"}),
        ]
    )
    result = DropEmptyColumnsPostProcessor().postprocess(tablesfile)
    rows = result.tables[0].get_table_fragments()[0].rows
    assert rows == [
        Row(family="Apiaceae"),
        Row(family="Fabaceae"),
    ]


def test_tablesfile_clone_overrides_tables_and_preserves_other_fields():
    original_tables: list[Table] = [
        TableWithFragments(table_fragments=[TableFragment(rows=[Row(name="Rosa")], page=1)])
    ]
    new_tables: list[Table] = [
        TableWithFragments(table_fragments=[TableFragment(rows=[Row(name="Canis lupus")], page=2)])
    ]
    original = TablesFile(
        tables=original_tables,
        citation="some citation",
        metadata=Metadata(filename="paper.pdf"),
        uuid="abc-123",
    )
    result = original.clone(tables=new_tables)
    assert result.tables == new_tables
    assert result.citation == "some citation"
    assert result.metadata == Metadata(filename="paper.pdf")
    assert result.uuid == "abc-123"


def test_tablesfile_clone_overrides_citation_and_preserves_other_fields():
    tables: list[Table] = [
        TableWithFragments(table_fragments=[TableFragment(rows=[Row(name="Rosa")], page=1)])
    ]
    original = TablesFile(tables=tables, citation="original citation", uuid="xyz-456")
    result = original.clone(citation="updated citation")
    assert result.tables == tables
    assert result.citation == "updated citation"
    assert result.uuid == "xyz-456"


def test_tablesfile_clone_with_no_overrides_returns_equal_instance():
    tables: list[Table] = [
        TableWithFragments(table_fragments=[TableFragment(rows=[Row(name="Rosa")], page=1)])
    ]
    original = TablesFile(tables=tables, citation="citation", uuid="abc")
    result = original.clone()
    assert result.tables == original.tables
    assert result.citation == original.citation
    assert result.uuid == original.uuid


def test_has_curations_false_when_no_metadata():
    tablesfile = TablesFile(tables=[], citation="")
    assert tablesfile.has_curations() is False


def test_has_curations_true_when_curations_present():
    tablesfile = TablesFile(
        tables=[],
        citation="",
        metadata=Metadata(
            filename=None,
            curations=[Curation(curator="alice", description="reviewed")],
        ),
    )
    assert tablesfile.has_curations() is True


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


def test_is_empty_value_float_is_not_empty():
    assert Row.is_empty_value(3.14) is False


def test_is_empty_value_zero_float_is_not_empty():
    assert Row.is_empty_value(0.0) is False


def test_is_empty_value_int_is_not_empty():
    assert Row.is_empty_value(42) is False


def test_is_empty_value_zero_int_is_not_empty():
    assert Row.is_empty_value(0) is False


def test_is_empty_value_bool_false_is_not_empty():
    assert Row.is_empty_value(False) is False


def test_is_empty_value_bool_true_is_not_empty():
    assert Row.is_empty_value(True) is False


def test_is_convergent_float():
    assert Row.is_convergent(3.14) is True


def test_is_convergent_int():
    assert Row.is_convergent(42) is True


def test_is_convergent_bool():
    assert Row.is_convergent(False) is True


def test_normalize_value_float_unchanged():
    assert Row.normalize_value(3.14) == 3.14


def test_normalize_value_int_unchanged():
    assert Row.normalize_value(42) == 42


def test_normalize_value_bool_unchanged():
    assert Row.normalize_value(True) is True


def test_row_is_empty_false_for_int_zero():
    assert Row(count=0).is_empty() is False


def test_row_is_empty_false_for_bool_false():
    assert Row(active=False).is_empty() is False


def test_row_is_empty_false_for_float():
    assert Row(ratio=3.14).is_empty() is False


_NATIVE_COERCE_SCHEMA = ColumnSchema({"count": int, "ratio": float, "active": bool})


def native_coerce_processor() -> SchemaPostProcessor:
    return SchemaPostProcessor(_NATIVE_COERCE_SCHEMA, coerce_types=True)


def test_coerce_native_int_value():
    result = native_coerce_processor().postprocess(wrap([Row(count=42)]))
    assert rows_of(result) == [Row(count=42)]


def test_coerce_native_float_value():
    result = native_coerce_processor().postprocess(wrap([Row(ratio=3.14)]))
    assert rows_of(result) == [Row(ratio=3.14)]


def test_coerce_native_bool_value():
    result = native_coerce_processor().postprocess(wrap([Row(active=True)]))
    assert rows_of(result) == [Row(active=True)]
