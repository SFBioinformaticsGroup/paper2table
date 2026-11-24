# pyright: reportCallIssue=false
import pytest
import re

from tablevalidate.schema import (
    Row,
    TableFragment,
    TablesFile,
    TableWithFragments,
    ValueWithAgreement,
)
from utils.column_schema import ColumnSchema
from utils.column_type import IntColumnType
from utils.column_value_normalizations import (
    ColumnValueNormalizationRule,
    parse_column_value_normalizations,
)
from utils.postprocessor import (
    NormalizeColumnValuePostProcessor,
    build_postprocessors,
)


# TODO reuse this helper
def wrap(rows: list[Row], page=1, citation="") -> TablesFile:
    return TablesFile(
        tables=[
            TableWithFragments(table_fragments=[TableFragment(rows=rows, page=page)])
        ],
        citation=citation,
    )


# TODO reuse this helper
def rows_of(tablesfile: TablesFile, table=0, fragment=0):
    return tablesfile.tables[table].get_table_fragments()[fragment].rows


def rule(column: str, original: str, replacement: str) -> ColumnValueNormalizationRule:
    return ColumnValueNormalizationRule(
        column=column, pattern=re.compile(original), replacement=replacement
    )


def test_parse_valid_line_produces_rule():
    rules = parse_column_value_normalizations("family:^foo$:bar")
    assert len(rules) == 1
    assert rules[0].column == "family"
    assert rules[0].pattern.pattern == "^foo$"
    assert rules[0].replacement == "bar"


def test_parse_skips_comment_and_blank_lines():
    text = "# a comment\n\nfamily:foo:bar\n  # trailing comment\n"
    rules = parse_column_value_normalizations(text)
    assert len(rules) == 1
    assert rules[0].column == "family"


def test_parse_fails_on_illformed_lines_():
    text = "family:onlytwo\nfamily:foo:bar\nbare\n"
    with pytest.raises(ValueError, match="Invalid rule"):
        parse_column_value_normalizations(text)


def test_parse_replacement_may_contain_colons():
    rules = parse_column_value_normalizations("notes:^a$:b:c:d")
    assert len(rules) == 1
    assert rules[0].replacement == "b:c:d"


def test_parse_invalid_regex_raises_value_error():
    with pytest.raises(ValueError, match="Invalid regex"):
        parse_column_value_normalizations("family:[unclosed:bar")


def test_single_value_cell_matching_is_replaced():
    result = NormalizeColumnValuePostProcessor(
        [rule("family", r"^Rosaceas$", "Rosaceae")]
    ).postprocess(wrap([Row(family="Rosaceas")]))
    assert rows_of(result) == [Row(family="Rosaceae")]


def test_single_value_cell_non_matching_is_untouched():
    result = NormalizeColumnValuePostProcessor(
        [rule("family", r"^Rosaceaee$", "Rosaceae")]
    ).postprocess(wrap([Row(family="Fabaceae")]))
    assert rows_of(result) == [Row(family="Fabaceae")]


def test_backreferences_in_replacement():
    result = NormalizeColumnValuePostProcessor(
        [rule("color", r"^(red|blue)\s+(.*)$", r"\2 (\1)")]
    ).postprocess(wrap([Row(color="red car")]))
    assert rows_of(result) == [Row(color="car (red)")]


def test_remove_sentinel_nullifies_matching_cell():
    result = NormalizeColumnValuePostProcessor(
        [rule("notes", r"^NR$", "<remove>")]
    ).postprocess(wrap([Row(notes="NR"), Row(notes="important")]))
    assert rows_of(result) == [Row(notes=None), Row(notes="important")]


def test_remove_sentinel_does_not_nullify_without_match():
    result = NormalizeColumnValuePostProcessor(
        [rule("notes", r"^NR$", "<remove>")]
    ).postprocess(wrap([Row(notes="keep this")]))
    assert rows_of(result) == [Row(notes="keep this")]


def test_matching_is_case_insensitive():
    rules = parse_column_value_normalizations("parte_usada:^hoja$:hojas")
    result = NormalizeColumnValuePostProcessor(rules).postprocess(
        wrap(
            [
                Row(parte_usada="Hoja"),
                Row(parte_usada="HOJA"),
                Row(parte_usada="hoja"),
            ]
        )
    )
    assert rows_of(result) == [
        Row(parte_usada="hojas"),
        Row(parte_usada="hojas"),
        Row(parte_usada="hojas"),
    ]


def test_other_columns_are_untouched():
    result = NormalizeColumnValuePostProcessor(
        [rule("color", r"red", "crimson")]
    ).postprocess(wrap([Row(color="red", family="red")]))
    assert rows_of(result) == [Row(color="crimson", family="red")]


def test_multiple_rules_on_same_column_apply_in_order():
    rules = [
        rule("size", r"\s*kg$", ""),
        rule("size", r"^(\d+)$", r"\1 kilograms"),
    ]
    result = NormalizeColumnValuePostProcessor(rules).postprocess(
        wrap([Row(size="23 kg")])
    )
    assert rows_of(result) == [Row(size="23 kilograms")]


def test_multivalued_cell_each_entry_is_rewritten():
    result = NormalizeColumnValuePostProcessor(
        [rule("family", r"^Rosaceaee$", "Rosaceae")]
    ).postprocess(
        wrap(
            [
                Row(
                    family=[
                        ValueWithAgreement(value="Rosaceaee", agreement_level=1),
                        ValueWithAgreement(value="Fabaceae", agreement_level=2),
                    ]
                )
            ]
        )
    )
    assert rows_of(result) == [
        Row(
            family=[
                ValueWithAgreement(value="Rosaceae", agreement_level=1),
                ValueWithAgreement(value="Fabaceae", agreement_level=2),
            ]
        )
    ]


def test_multivalued_cell_compacts_duplicates_summing_agreement():
    result = NormalizeColumnValuePostProcessor(
        [rule("family", r"^Rosaceaee$", "Rosaceae")]
    ).postprocess(
        wrap(
            [
                Row(
                    family=[
                        ValueWithAgreement(value="Rosaceaee", agreement_level=1),
                        ValueWithAgreement(value="Rosaceae", agreement_level=2),
                    ]
                )
            ]
        )
    )
    assert rows_of(result) == [
        Row(family=[ValueWithAgreement(value="Rosaceae", agreement_level=3)])
    ]


def test_multivalued_cell_remove_sentinel_nullifies_entry():
    result = NormalizeColumnValuePostProcessor(
        [rule("notes", r"^NR$", "<remove>")]
    ).postprocess(
        wrap(
            [
                Row(
                    notes=[
                        ValueWithAgreement(value="NR", agreement_level=1),
                        ValueWithAgreement(value="important", agreement_level=2),
                    ]
                )
            ]
        )
    )
    assert rows_of(result) == [
        Row(
            notes=[
                ValueWithAgreement(value=None, agreement_level=1),
                ValueWithAgreement(value="important", agreement_level=2),
            ]
        )
    ]


def test_preserves_citation_and_metadata():
    source = wrap([Row(family="Rosaceaee")], citation="my citation")
    result = NormalizeColumnValuePostProcessor(
        [rule("family", r"^Rosaceaee$", "Rosaceae")]
    ).postprocess(source)
    assert result.citation == "my citation"


def test_runs_before_drop_empty_columns_in_chain():
    normalization = [rule("notes", r".+", "<remove>")]
    postprocessors = build_postprocessors(
        schema=None,
        filter_columns=False,
        order_columns=False,
        coerce_types=False,
        column_value_normalizations=normalization,
    )
    tablesfile = wrap([Row(family="Rosaceae", notes="junk")])
    for postprocessor in postprocessors:
        tablesfile = postprocessor.postprocess(tablesfile)
    assert rows_of(tablesfile) == [Row(family="Rosaceae")]


def test_runs_before_schema_coerce_in_chain():
    normalization = [rule("year", r"^MCMXCIX$", "1999")]
    schema = ColumnSchema({"year": IntColumnType()})
    postprocessors = build_postprocessors(
        schema=schema,
        filter_columns=False,
        order_columns=False,
        coerce_types=True,
        column_value_normalizations=normalization,
    )
    tablesfile = wrap([Row(year="MCMXCIX")])
    for postprocessor in postprocessors:
        tablesfile = postprocessor.postprocess(tablesfile)
    assert rows_of(tablesfile) == [Row(year=1999)]
