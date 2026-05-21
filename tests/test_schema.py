# pyright: reportCallIssue=false
from tablemerge.schema import SchemaPostProcessor
from utils.coerce import coerce_str
from tablevalidate.schema import (
    TablesFile,
    TableWithFragments,
    TableFragment,
    Row,
    ValueWithAgreement,
)


def wrap(rows: list[Row], page=1, citation="") -> TablesFile:
    return TablesFile(
        tables=[TableWithFragments(table_fragments=[TableFragment(rows=rows, page=page)])],
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
    return tf.tables[table].table_fragments[fragment].rows


# ---------------------------------------------------------------------------
# coerce_str
# ---------------------------------------------------------------------------

class TestCoerceStr:
    def test_str_is_noop(self):
        assert coerce_str("hello", str) == "hello"

    def test_int_normalizes_float_string(self):
        assert coerce_str("42.0", int) == "42"

    def test_int_plain(self):
        assert coerce_str("7", int) == "7"

    def test_int_invalid_leaves_unchanged(self):
        assert coerce_str("N/A", int) == "N/A"

    def test_float_from_int_string(self):
        assert coerce_str("1", float) == "1.0"

    def test_float_plain(self):
        assert coerce_str("3.14", float) == "3.14"

    def test_float_invalid_leaves_unchanged(self):
        assert coerce_str("abc", float) == "abc"

    def test_bool_truthy_words(self):
        for word in ("true", "True", "TRUE", "1", "yes", "YES", "on", "ON"):
            assert coerce_str(word, bool) == "True", word

    def test_bool_falsy_words(self):
        for word in ("false", "False", "FALSE", "0", "no", "NO", "off", "OFF"):
            assert coerce_str(word, bool) == "False", word

    def test_bool_unrecognised_leaves_unchanged(self):
        assert coerce_str("maybe", bool) == "maybe"


# ---------------------------------------------------------------------------
# filter_columns
# ---------------------------------------------------------------------------

class TestFilterSchemaColumns:
    SCHEMA = {"name": (str, ...), "species": (str, ...)}

    def proc(self) -> SchemaPostProcessor:
        return SchemaPostProcessor(self.SCHEMA, filter_columns=True)

    def test_keeps_table_with_matching_column(self):
        result = self.proc().postprocess(wrap([Row(name="foo")]))
        assert len(result.tables) == 1

    def test_drops_table_with_no_matching_column(self):
        result = self.proc().postprocess(wrap([Row(color="red", size="big")]))
        assert len(result.tables) == 0

    def test_keeps_table_with_partial_match(self):
        result = self.proc().postprocess(wrap([Row(species="Canis lupus", habitat="forest")]))
        assert len(result.tables) == 1

    def test_mixed_tables(self):
        tf = wrap_two_tables([Row(name="Rosa")], [Row(color="red")])
        result = self.proc().postprocess(tf)
        assert len(result.tables) == 1

    def test_preserves_citation(self):
        result = self.proc().postprocess(wrap([Row(name="x")], citation="some citation"))
        assert result.citation == "some citation"

    def test_all_tables_dropped_returns_empty(self):
        tf = wrap_two_tables([Row(color="red")], [Row(size="big")])
        result = self.proc().postprocess(tf)
        assert result.tables == []


# ---------------------------------------------------------------------------
# order_columns
# ---------------------------------------------------------------------------

class TestOrderSchemaColumns:
    SCHEMA = {"name": (str, ...), "species": (str, ...), "family": (str, ...)}

    def proc(self) -> SchemaPostProcessor:
        return SchemaPostProcessor(self.SCHEMA, order_columns=True)

    def test_schema_columns_come_first(self):
        result = self.proc().postprocess(wrap([Row(habitat="forest", name="Rosa", family="Rosaceae")]))
        cols = list(rows_of(result)[0].get_columns().keys())
        assert cols.index("name") < cols.index("habitat")
        assert cols.index("family") < cols.index("habitat")

    def test_schema_order_respected(self):
        result = self.proc().postprocess(wrap([Row(family="Rosaceae", species="Rosa canina", name="Dog rose")]))
        cols = list(rows_of(result)[0].get_columns().keys())
        assert cols[:3] == ["name", "species", "family"]

    def test_missing_schema_columns_not_inserted(self):
        result = self.proc().postprocess(wrap([Row(name="Rosa")]))
        cols = list(rows_of(result)[0].get_columns().keys())
        assert cols == ["name"]

    def test_preserves_metadata(self):
        result = self.proc().postprocess(wrap([Row(name="Rosa", agreement_level_=3, sources_=["uuid1"])]))
        row = rows_of(result)[0]
        assert row.agreement_level_ == 3
        assert row.sources_ == ["uuid1"]


# ---------------------------------------------------------------------------
# coerce_types
# ---------------------------------------------------------------------------

class TestCoerceSchemaColumnTypes:
    SCHEMA = {"year": (int, ...), "length": (float, ...), "active": (bool, ...), "label": (str, ...)}

    def proc(self) -> SchemaPostProcessor:
        return SchemaPostProcessor(self.SCHEMA, coerce_types=True)

    def cols(self, tf: TablesFile) -> dict:
        return rows_of(tf)[0].get_columns()

    def test_int_coercion(self):
        assert self.cols(self.proc().postprocess(wrap([Row(year="2020.0")])))["year"] == "2020"

    def test_float_coercion(self):
        assert self.cols(self.proc().postprocess(wrap([Row(length="3")])))["length"] == "3.0"

    def test_bool_coercion_true(self):
        assert self.cols(self.proc().postprocess(wrap([Row(active="yes")])))["active"] == "True"

    def test_bool_coercion_false(self):
        assert self.cols(self.proc().postprocess(wrap([Row(active="no")])))["active"] == "False"

    def test_str_is_noop(self):
        assert self.cols(self.proc().postprocess(wrap([Row(label="hello")])))["label"] == "hello"

    def test_unconvertible_left_unchanged(self):
        assert self.cols(self.proc().postprocess(wrap([Row(year="N/A")])))["year"] == "N/A"

    def test_non_schema_column_untouched(self):
        assert self.cols(self.proc().postprocess(wrap([Row(color="red")])))["color"] == "red"

    def test_value_with_agreement_coerced(self):
        tf = wrap([Row(year=[
            ValueWithAgreement(value="2020.0", agreement_level=2),
            ValueWithAgreement(value="bad", agreement_level=1),
        ])])
        values = self.cols(self.proc().postprocess(tf))["year"]
        assert isinstance(values, list)
        assert values[0].value == "2020"
        assert values[1].value == "bad"
        assert values[0].agreement_level == 2

    def test_preserves_metadata(self):
        result = self.proc().postprocess(wrap([Row(year="2020", agreement_level_=2, sources_=["u1"])]))
        row = rows_of(result)[0]
        assert row.agreement_level_ == 2
        assert row.sources_ == ["u1"]
