# pyright: reportCallIssue=false
from table2html.__main__ import (
    agreement_css_class,
    build_css,
    build_data_rows,
    build_fragment_html,
    build_html,
    build_metadata_html,
    build_paper_curations_html,
    render_citation,
)
from tablevalidate.schema import (
    Curation,
    Metadata,
    Row,
    TableFragment,
    TablesFile,
    ValueWithAgreement,
)


def joined(parts):
    return "\n".join(parts)


def test_fragment_no_rows():
    out = joined(build_fragment_html(1, TableFragment(page=3, rows=[])))
    assert "Table 1, page 3" in out
    assert "No rows" in out
    assert "<table" not in out


def test_fragment_renders_header_and_row():
    fragment = TableFragment(page=1, rows=[Row(species="Rosa", family="Rosaceae")])
    out = joined(build_fragment_html(1, fragment))
    assert "<th>species</th>" in out
    assert "<th>family</th>" in out
    assert "<td>Rosa</td>" in out
    assert "<td>Rosaceae</td>" in out


def test_fragment_readers_before_sources():
    fragment = TableFragment(page=1, rows=[Row(species="Rosa", sources_=["s1"])])
    uuid_to_reader = {"s1": "pdfplumber"}
    out = joined(build_fragment_html(1, fragment, uuid_to_reader))
    headers = [h.strip() for h in out.split("<th>")[1:]]
    assert headers[0].startswith("species")
    assert headers[-2].startswith("readers_")
    assert headers[-1].startswith("sources_")


def test_fragment_readers_hidden_without_uuid_mapping():
    fragment = TableFragment(page=1, rows=[Row(species="Rosa", sources_=["s1"])])
    out = joined(build_fragment_html(1, fragment))
    assert "readers_" not in out
    assert "sources_" in out


def test_fragment_agreement_level_column_shown_first():
    fragment = TableFragment(page=1, rows=[Row(species="Rosa", agreement_level_=2)])
    out = joined(build_fragment_html(1, fragment))
    headers = [h.split("</th>")[0] for h in out.split("<th>")[1:]]
    assert headers[0] == "agreement_level_"
    assert "<td class='medium'>2</td>" in out


def test_fragment_no_agreement_level_column_when_absent():
    fragment = TableFragment(page=1, rows=[Row(species="Rosa")])
    out = joined(build_fragment_html(1, fragment))
    assert "agreement_level_" not in out


def test_fragment_non_common_column_appears_in_header():
    fragment = TableFragment(
        page=1,
        rows=[
            Row(species="Rosa", family="Rosaceae"),
            Row(species="Mentha", note="fragrant"),
        ],
    )
    out = joined(build_fragment_html(1, fragment))
    assert "<th>species</th>" in out
    assert "<th>family</th>" in out
    assert "<th>note</th>" in out


def test_fragment_non_common_column_ordering():
    fragment = TableFragment(
        page=1,
        rows=[
            Row(species="Rosa", family="Rosaceae"),
            Row(species="Mentha", note="fragrant"),
        ],
    )
    out = joined(build_fragment_html(1, fragment))
    headers = [h.split("</th>")[0] for h in out.split("<th>")[1:]]
    assert headers[0] == "species"
    assert "family" in headers
    assert "note" in headers
    assert headers.index("species") < headers.index("family")
    assert headers.index("species") < headers.index("note")


def test_fragment_non_common_column_empty_for_missing_rows():
    fragment = TableFragment(
        page=1,
        rows=[
            Row(species="Rosa", family="Rosaceae"),
            Row(species="Mentha", note="fragrant"),
        ],
    )
    out = joined(build_fragment_html(1, fragment))
    assert "<td>Rosa</td>" in out
    assert "<td>Mentha</td>" in out


def test_fragment_readers_column_shows_readers():
    fragment = TableFragment(page=1, rows=[Row(species="Rosa", sources_=["s1", "s2"])])
    uuid_to_reader = {"s1": "pdfplumber", "s2": "camelot"}
    out = joined(build_fragment_html(1, fragment, uuid_to_reader))
    assert "pdfplumber" in out
    assert "camelot" in out


def test_fragment_readers_column_deduplicates():
    fragment = TableFragment(page=1, rows=[Row(species="Rosa", sources_=["s1", "s2"])])
    uuid_to_reader = {"s1": "pdfplumber", "s2": "pdfplumber"}
    out = joined(build_fragment_html(1, fragment, uuid_to_reader))
    assert "<td>pdfplumber</td>" in out


def test_fragment_multivalued_expands_to_rows():
    fragment = TableFragment(
        page=1,
        rows=[
            Row(
                family="Apiaceae",
                species=[
                    ValueWithAgreement(value="Ammi majus", agreement_level=1),
                    ValueWithAgreement(value="Carum carvi", agreement_level=1),
                ],
            )
        ],
    )
    out = joined(build_fragment_html(1, fragment))
    assert "rowspan='2'" in out
    assert "<td rowspan='2'>Apiaceae</td>" in out
    assert "Ammi majus" in out
    assert "Carum carvi" in out


def test_fragment_agreement_css_low():
    fragment = TableFragment(page=1, rows=[Row(x="v", agreement_level_=1)])
    out = joined(build_fragment_html(1, fragment))
    assert "class='low'" in out


def test_fragment_agreement_css_medium():
    fragment = TableFragment(page=1, rows=[Row(x="v", agreement_level_=2)])
    out = joined(build_fragment_html(1, fragment))
    assert "class='medium'" in out


def test_fragment_agreement_css_high():
    fragment = TableFragment(page=1, rows=[Row(x="v", agreement_level_=3)])
    out = joined(build_fragment_html(1, fragment))
    assert "class='high'" in out


def test_metadata_scalar_fields_rendered():
    out = joined(build_metadata_html({"tool": "paper2table", "version": "1.0"}))
    assert "<th>tool</th>" in out
    assert "<td>paper2table</td>" in out


def test_metadata_sources_table_rendered():
    metadata = {
        "sources": [
            {"id": "abc", "reader": "pdfplumber", "path": "/tmp/a.pdf"},
        ]
    }
    out = joined(build_metadata_html(metadata))
    assert "<h3>Sources</h3>" in out
    assert "abc" in out
    assert "/tmp/a.pdf" in out


def test_metadata_sources_preferred_column_order():
    metadata = {
        "sources": [{"id": "u1", "reader": "camelot", "path": "/p", "extra": "e"}]
    }
    out = joined(build_metadata_html(metadata))
    headers = [h.split("</th>")[0] for h in out.split("<th>")[1:]]
    assert headers[:3] == ["id", "reader", "path"]


def test_metadata_no_sources_key():
    out = joined(build_metadata_html({"tool": "x"}))
    assert "Sources" not in out


def test_build_html_structure():
    out = build_html({}, {}, {})
    assert "<!DOCTYPE html>" in out
    assert "<title>Paper2Table Viewer</title>" in out
    assert "</html>" in out


def test_build_html_no_metadata_section_when_empty():
    out = build_html({}, {}, {})
    assert "<h2>Metadata</h2>" not in out


def test_build_html_includes_paper():
    papers = {"mypaper.tables.json": TablesFile(citation="Smith 2020", tables=[])}
    out = build_html({}, {}, papers)
    assert "mypaper.tables.json" in out
    assert "Smith 2020" in out


def test_is_empty_row_true_when_only_meta():
    assert Row(agreement_level_=2, sources_=["s1"]).is_empty()


def test_is_empty_row_true_when_blank_content():
    assert Row(species="", agreement_level_=1).is_empty()


def test_is_empty_row_false_when_has_content():
    assert not Row(species="Rosa", agreement_level_=1).is_empty()


def test_fragment_skips_empty_rows_and_shows_legend():
    fragment = TableFragment(
        page=1,
        rows=[
            Row(species="Rosa", family="Rosaceae"),
            Row(species="", family=""),
            Row(species="", family=""),
        ],
    )
    out = joined(build_fragment_html(1, fragment))
    assert "Rosa" in out
    assert "(2 empty rows not shown)" in out


def test_fragment_all_empty_rows_no_table():
    fragment = TableFragment(page=1, rows=[Row(species=""), Row(species="")])
    out = joined(build_fragment_html(1, fragment))
    assert "<table" not in out
    assert "(2 empty rows not shown)" in out


def test_agreement_css_class_low_zero():
    assert agreement_css_class(0) == "low"


def test_agreement_css_class_low_one():
    assert agreement_css_class(1) == "low"


def test_agreement_css_class_medium():
    assert agreement_css_class(2) == "medium"


def test_agreement_css_class_high():
    assert agreement_css_class(3) == "high"


def test_build_data_rows_simple():
    row = Row(species="Rosa", family="Rosaceae")
    out = joined(build_data_rows(row, ["species", "family"]))
    assert "<td>Rosa</td>" in out
    assert "<td>Rosaceae</td>" in out


def test_build_data_rows_applies_css_class():
    row = Row(x="v", agreement_level_=2)
    out = joined(build_data_rows(row, ["x", "agreement_level_"]))
    assert "class='medium'" in out


def test_build_data_rows_automatic_curation_icon():
    row = Row(agreement_level_=2, curation_type_="automatic")
    out = build_data_rows(row, ["agreement_level_"])
    assert out == [
        "<tr>",
        "<td class='medium'>2 <span class='curation-icon' title='Automatically curated'>🤖</span></td>",
        "</tr>",
    ]


def test_build_data_rows_manual_curation_icon():
    row = Row(agreement_level_=3, curation_type_="manual")
    out = build_data_rows(row, ["agreement_level_"])
    assert out == [
        "<tr>",
        "<td class='high'>3 <span class='curation-icon' title='Manually curated'>✍️</span></td>",
        "</tr>",
    ]


def test_build_data_rows_no_curation_icon_when_none():
    row = Row(agreement_level_=2, curation_type_="none")
    out = build_data_rows(row, ["agreement_level_"])
    assert out == [
        "<tr>",
        "<td class='medium'>2</td>",
        "</tr>",
    ]


def test_build_data_rows_no_curation_icon_when_null():
    row = Row(agreement_level_=2)
    out = build_data_rows(row, ["agreement_level_"])
    assert out == [
        "<tr>",
        "<td class='medium'>2</td>",
        "</tr>",
    ]


def test_paper_curations_html_empty_omits_section():
    assert build_paper_curations_html([]) == []


def test_paper_curations_html_renders_rows():
    curations = [
        Curation(curator="alice", timestamp="2026-01-02", description="fixed units"),
        Curation(curator="bob", timestamp=None, description=None),
    ]
    out = joined(build_paper_curations_html(curations))
    assert "<summary>Curations (2)</summary>" in out
    assert "<th>curator</th><th>timestamp</th><th>description</th>" in out
    assert "<td>alice</td><td>2026-01-02</td><td>fixed units</td>" in out
    assert "<td>bob</td><td></td><td></td>" in out


def test_build_html_renders_paper_curations_from_metadata():
    papers = {
        "paper.tables.json": TablesFile(
            citation="Smith 2020",
            tables=[],
            metadata=Metadata(
                filename=None,
                curations=[Curation(curator="alice", description="review", timestamp="2026-01-02")],
            ),
        )
    }
    out = build_html({}, {}, papers)
    assert "<summary>Curations (1)</summary>" in out
    assert "<td>alice</td><td>2026-01-02</td><td>review</td>" in out


def test_build_html_omits_paper_curations_when_metadata_missing():
    papers = {"paper.tables.json": TablesFile(citation="Smith 2020", tables=[])}
    out = build_html({}, {}, papers)
    assert "<details class='paper-curations'>" not in out


def test_build_data_rows_readers_column():
    row = Row(species="Rosa", sources_=["s1", "s2"])
    uuid_to_reader = {"s1": "pdfplumber", "s2": "camelot"}
    out = joined(build_data_rows(row, ["species", "readers_"], uuid_to_reader))
    assert "pdfplumber" in out
    assert "camelot" in out


def test_build_data_rows_multivalued_expands():
    row = Row(
        family="Apiaceae",
        species=[
            ValueWithAgreement(value="Ammi majus", agreement_level=1),
            ValueWithAgreement(value="Carum carvi", agreement_level=2),
        ],
    )
    out = joined(build_data_rows(row, ["family", "species"]))
    assert "rowspan='2'" in out
    assert "<td rowspan='2'>Apiaceae</td>" in out
    assert "Ammi majus" in out
    assert "Carum carvi" in out


def test_build_data_rows_multivalued_agreement_css():
    row = Row(
        agreement_level_=4,
        species=[
            ValueWithAgreement(value="Ammi majus", agreement_level=1),
            ValueWithAgreement(value="Carum carvi", agreement_level=2),
        ],
    )
    out = joined(build_data_rows(row, ["species"]))
    assert "class='low'" in out
    assert "class='medium'" in out


def test_build_data_rows_list_value_single_element():
    row = Row(tags=[ValueWithAgreement(value="a", agreement_level=1)])
    out = joined(build_data_rows(row, ["tags"]))
    assert "<td>a</td>" in out


def test_build_css_contains_body_rule():
    css = "\n".join(build_css())
    assert "font-family: Arial" in css


def test_build_css_contains_agreement_classes():
    css = "\n".join(build_css())
    assert ".low { background-color: #fdd; }" in css
    assert ".medium { background-color: #ffd; }" in css
    assert ".high { background-color: #dfd; }" in css


def test_render_citation_none():
    assert render_citation(None) == []


def test_render_citation_string():
    assert render_citation("Smith 2020") == ["Smith 2020"]



def test_build_fragment_html_no_rowspan_without_multivalued():
    fragment = TableFragment(
        page=1,
        rows=[
            Row(family="Apiaceae", species="Ammi majus"),
            Row(family="Apiaceae", species="Carum carvi"),
        ],
    )
    out = joined(build_fragment_html(1, fragment))
    assert "rowspan" not in out


def test_build_data_rows_renders_float():
    row = Row(ratio=3.14)
    html = joined(build_data_rows(row, ["ratio"]))
    assert "<td>3.14</td>" in html


def test_build_data_rows_renders_int_zero_not_empty():
    row = Row(count=0)
    html = joined(build_data_rows(row, ["count"]))
    assert "<td>0</td>" in html


def test_build_data_rows_renders_bool_false_not_empty():
    row = Row(active=False)
    html = joined(build_data_rows(row, ["active"]))
    assert "<td>False</td>" in html


def test_build_data_rows_renders_bool_true():
    row = Row(active=True)
    html = joined(build_data_rows(row, ["active"]))
    assert "<td>True</td>" in html


def test_build_fragment_html_renders_int_cell():
    fragment = TableFragment(page=1, rows=[Row(count=42)])
    out = joined(build_fragment_html(1, fragment))
    assert "<td>42</td>" in out


def test_fragment_keeps_rows_whose_only_value_is_na_value():
    """table2html treats only "" / None as blank. A row with value "none"
    is rendered, not hidden."""
    fragment = TableFragment(
        page=1,
        rows=[
            Row(species="Rosa"),
            Row(species="none"),
        ],
    )
    out = joined(build_fragment_html(1, fragment))
    assert "Rosa" in out
    assert "none" in out
    assert "empty rows not shown" not in out
