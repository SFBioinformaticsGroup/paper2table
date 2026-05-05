from table2html.__main__ import build_fragment_html, build_metadata_html, build_html


def joined(parts):
    return "\n".join(parts)


def test_fragment_no_rows():
    out = joined(build_fragment_html(1, {"page": 3, "rows": []}))
    assert "Table 1, page 3" in out
    assert "No rows" in out
    assert "<table" not in out


def test_fragment_renders_header_and_row():
    fragment = {"page": 1, "rows": [{"species": "Rosa", "family": "Rosaceae"}]}
    out = joined(build_fragment_html(1, fragment))
    assert "<th>species</th>" in out
    assert "<th>family</th>" in out
    assert "<td>Rosa</td>" in out
    assert "<td>Rosaceae</td>" in out


def test_fragment_sources_column_last():
    fragment = {
        "page": 1,
        "rows": [{"sources_": ["s1"], "species": "Rosa"}],
    }
    out = joined(build_fragment_html(1, fragment))
    headers = [h.strip() for h in out.split("<th>")[1:]]
    assert headers[0].startswith("species")
    assert headers[-1].startswith("sources_")


def test_fragment_list_value_joined():
    fragment = {"page": 1, "rows": [{"tags": ["a", "b", "c"]}]}
    out = joined(build_fragment_html(1, fragment))
    assert "<td>a, b, c</td>" in out


def test_fragment_agreement_css_low():
    fragment = {"page": 1, "rows": [{"x": "v", "agreement_level_": 1}]}
    out = joined(build_fragment_html(1, fragment))
    assert "class='low'" in out


def test_fragment_agreement_css_medium():
    fragment = {"page": 1, "rows": [{"x": "v", "agreement_level_": 2}]}
    out = joined(build_fragment_html(1, fragment))
    assert "class='medium'" in out


def test_fragment_agreement_css_high():
    fragment = {"page": 1, "rows": [{"x": "v", "agreement_level_": 3}]}
    out = joined(build_fragment_html(1, fragment))
    assert "class='high'" in out


def test_metadata_scalar_fields_rendered():
    out = joined(build_metadata_html({"tool": "paper2table", "version": "1.0"}))
    assert "<th>tool</th>" in out
    assert "<td>paper2table</td>" in out


def test_metadata_sources_table_rendered():
    metadata = {
        "sources": [
            {"uuid": "abc", "reader": "pdfplumber", "path": "/tmp/a.pdf"},
        ]
    }
    out = joined(build_metadata_html(metadata))
    assert "<h3>Sources</h3>" in out
    assert "abc" in out
    assert "/tmp/a.pdf" in out


def test_metadata_sources_preferred_column_order():
    metadata = {
        "sources": [{"uuid": "u1", "reader": "camelot", "path": "/p", "extra": "e"}]
    }
    out = joined(build_metadata_html(metadata))
    headers = [h.split("</th>")[0] for h in out.split("<th>")[1:]]
    assert headers[:3] == ["uuid", "reader", "path"]


def test_metadata_no_sources_key():
    out = joined(build_metadata_html({"tool": "x"}))
    assert "Sources" not in out


def test_build_html_structure():
    out = build_html({}, {})
    assert "<!DOCTYPE html>" in out
    assert "<title>Paper2Table Viewer</title>" in out
    assert "</html>" in out


def test_build_html_no_metadata_section_when_empty():
    out = build_html({}, {})
    assert "<h2>Metadata</h2>" not in out


def test_build_html_includes_paper():
    papers = {"mypaper.tables.json": {"citation": "Smith 2020", "tables": []}}
    out = build_html({}, papers)
    assert "mypaper.tables.json" in out
    assert "Smith 2020" in out
