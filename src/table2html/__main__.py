import argparse
import json
import webbrowser
from pathlib import Path

from utils.rows import is_empty_row
from utils.table_fragments import load_papers
from tablevalidate.schema import (
    Citation,
    Row,
    TablesFile,
    TableFragment,
)


def load_papers_with_metadata(directory: Path) -> tuple[dict, dict[str, TablesFile]]:
    metadata: dict = {}
    metadata_file = directory / "tables.metadata.json"
    if metadata_file.exists():
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
    if metadata.get("reader") == "tablemerge" and "agreement_method" not in metadata:
        metadata = {**metadata, "agreement_method": "simple-count"}
    return metadata, load_papers(directory)


def _reader_emoji(reader: str) -> str:
    if not reader:
        return ""
    if reader in ("pdfplumber", "camelot", "pymupdf"):
        return "💻"
    if reader.startswith("hybrid-"):
        return "☯️"
    return "🤖"


def _source_cell(source: dict, key: str) -> str:
    value = source.get(key, "")
    if key == "uuid":
        emoji = _reader_emoji(source.get("reader", ""))
        return f"{emoji} {value}" if emoji else value
    return value


def render_citation(citation: Citation) -> str:
    if citation is None:
        return ""
    if isinstance(citation, list):
        return ", ".join(v.value for v in citation)
    return citation


def build_toc(papers: dict[str, TablesFile]) -> list[str]:
    html = ['<nav id="toc">', '<div id="toc-inner">', "<b>Contents</b>", "<ul>"]
    for paper_i, (paper_name, content) in enumerate(papers.items()):
        paper_id = f"paper-{paper_i}"
        html.append(f'<li><a href="#{paper_id}">{paper_name}</a>')
        fragments = [
            (idx, fragment)
            for idx, table in enumerate(content.tables, 1)
            for fragment in table.get_table_fragments()
        ]
        if fragments:
            html.append("<ul>")
            for idx, fragment in fragments:
                frag_id = f"paper-{paper_i}-table-{idx}-page-{fragment.page}"
                html.append(
                    f'<li><a href="#{frag_id}">Table {idx}, p.&nbsp;{fragment.page}</a></li>'
                )
            html.append("</ul>")
        html.append("</li>")
    html.extend(["</ul>", "</div>", "</nav>"])
    return html


def flatten_dict(data: dict, prefix: str, rows: list[tuple[str, str]]) -> None:
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flatten_dict(value, full_key, rows)
        elif isinstance(value, list):
            rows.append((full_key, ", ".join(str(v) for v in value)))
        else:
            rows.append((full_key, str(value)))


def flatten_metadata_rows(metadata: dict) -> list[tuple[str, str]]:
    rows = []
    for key, value in metadata.items():
        if key == "sources":
            continue
        if isinstance(value, dict):
            flatten_dict(value, "", rows)
        elif isinstance(value, list):
            rows.append((key, ", ".join(str(v) for v in value)))
        else:
            rows.append((key, str(value)))
    return rows


def build_metadata_html(metadata: dict) -> list[str]:
    html = ["<h2>Metadata</h2>"]
    rows = flatten_metadata_rows(metadata)
    if rows:
        html.append("<div class='table-wrapper'><table class='table metadata-table'>")
        for key, value in rows:
            html.append(f"<tr><th>{key}</th><td>{value}</td></tr>")
        html.append("</table></div>")
    sources = metadata.get("sources")
    if sources:
        html.append("<h3>Sources</h3>")
        all_keys = {k for s in sources for k in s}
        preferred = ["uuid", "reader", "path"]
        source_keys = [k for k in preferred if k in all_keys] + sorted(
            all_keys - set(preferred)
        )
        html.append("<div class='table-wrapper'><table class='table'>")
        html.append("<tr>" + "".join(f"<th>{k}</th>" for k in source_keys) + "</tr>")
        for source in sources:
            html.append(
                "<tr>"
                + "".join(f"<td>{_source_cell(source, k)}</td>" for k in source_keys)
                + "</tr>"
            )
        html.append("</table></div>")
    return html


def agreement_css_class(level: int) -> str:
    if level <= 1:
        return "low"
    if level == 2:
        return "medium"
    return "high"


def build_data_row(
    row: Row,
    columns: list[str],
    uuid_to_reader: dict[str, str] | None = None,
) -> list[str]:
    css_class = agreement_css_class(row.agreement_level_ or 0)
    html = [f"<tr class='{css_class}'>"]
    col_values = row.get_columns()
    for col in columns:
        if col == "agreement_level_":
            val = str(row.agreement_level_) if row.agreement_level_ is not None else ""
        elif col == "readers_":
            source_ids = row.sources_ or []
            mapping = uuid_to_reader or {}
            readers = list(
                dict.fromkeys(mapping[sid] for sid in source_ids if sid in mapping)
            )
            val = ", ".join(readers)
        elif col == "sources_":
            val = ", ".join(row.sources_ or [])
        else:
            cell = col_values.get(col, "")
            if isinstance(cell, list):
                val = ", ".join(v.value for v in cell)
            else:
                val = cell or ""
        html.append(f"<td>{val}</td>")
    html.append("</tr>")
    return html


def collect_paper_source_uuids(content: TablesFile) -> set[str]:
    uuids: set[str] = set()
    for table in content.tables:
        for fragment in table.get_table_fragments():
            for row in fragment.rows:
                for uid in row.sources_ or []:
                    uuids.add(uid)
    return uuids


def build_paper_sources_html(sources: list[dict]) -> list[str]:
    if not sources:
        return []
    all_keys = {k for s in sources for k in s}
    preferred = ["uuid", "reader", "path"]
    source_keys = [k for k in preferred if k in all_keys] + sorted(
        all_keys - set(preferred)
    )
    html = ["<details class='paper-sources'>"]
    html.append(f"<summary>Sources ({len(sources)})</summary>")
    html.append("<div class='table-wrapper'><table class='table'>")
    html.append("<tr>" + "".join(f"<th>{k}</th>" for k in source_keys) + "</tr>")
    for source in sources:
        html.append(
            "<tr>"
            + "".join(f"<td>{_source_cell(source, k)}</td>" for k in source_keys)
            + "</tr>"
        )
    html.append("</table></div></details>")
    return html


def build_fragment_html(
    idx: int,
    fragment: TableFragment,
    uuid_to_reader: dict[str, str] | None = None,
    anchor_id: str | None = None,
) -> list[str]:
    id_attr = f' id="{anchor_id}"' if anchor_id else ""
    html = [f"<h4{id_attr}>Table {idx}, page {fragment.page}</h4>"]
    all_rows = fragment.rows
    rows = [r for r in all_rows if not is_empty_row(r)]
    skipped = len(all_rows) - len(rows)
    if not rows:
        html.append("<p><i>No rows</i></p>")
        if skipped:
            html.append(f"<p><i>({skipped} empty rows not shown)</i></p>")
        return html
    has_agreement = any(r.agreement_level_ is not None for r in rows)
    has_sources = any(r.sources_ is not None for r in rows)
    all_col_names = Row.column_names(rows)
    row_col_sets = [set(row.get_columns()) for row in rows]
    common_cols = [c for c in all_col_names if all(c in s for s in row_col_sets)]
    extra_cols = [c for c in all_col_names if c not in common_cols]
    columns = []
    if has_agreement:
        columns.append("agreement_level_")
    columns.extend(common_cols)
    columns.extend(extra_cols)
    if has_sources:
        columns.append("readers_")
        columns.append("sources_")
    html.append("<div class='table-wrapper'><table class='table'>")
    html.append("<tr>" + "".join(f"<th>{col}</th>" for col in columns) + "</tr>")
    for row in rows:
        html.extend(build_data_row(row, columns, uuid_to_reader))
    html.append("</table></div>")
    if skipped:
        html.append(f"<p><i>({skipped} empty rows not shown)</i></p>")
    return html


_TOC_JS = """\
(function () {
  var entries = Array.from(document.querySelectorAll('#toc a')).map(function (a) {
    var id = a.getAttribute('href').slice(1);
    return { el: document.getElementById(id), a: a };
  }).filter(function (x) { return x.el; });

  function update() {
    var scrollY = window.scrollY + 8;
    var active = null;
    for (var i = 0; i < entries.length; i++) {
      if (entries[i].el.getBoundingClientRect().top + window.scrollY <= scrollY) {
        active = entries[i];
      } else {
        break;
      }
    }
    entries.forEach(function (e) { e.a.classList.remove('active'); });
    if (active) {
      active.a.classList.add('active');
      active.a.scrollIntoView({ block: 'nearest' });
    }
  }

  window.addEventListener('scroll', update, { passive: true });
  update();
}());
"""


def build_css() -> list[str]:
    return [
        "* { box-sizing: border-box; }",
        "body { font-family: Arial, sans-serif; display: flex;"
        " align-items: flex-start; margin: 0; }",
        "#toc { width: 240px; flex-shrink: 0; position: sticky; top: 0; height: 100vh;"
        " overflow-y: auto; border-right: 1px solid #ddd;"
        " background: #f5f5f5; padding: 12px; }",
        "#toc b { display: block; margin-bottom: 8px; color: #555; font-size: 0.82em;"
        " text-transform: uppercase; letter-spacing: 0.05em; }",
        "#toc ul { list-style: none; margin: 0; padding: 0; }",
        "#toc ul ul { padding-left: 12px; }",
        "#toc li { margin: 1px 0; }",
        "#toc a { display: block; padding: 3px 6px; border-radius: 3px;"
        " text-decoration: none; color: #333; font-size: 0.82em;"
        " white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }",
        "#toc a:hover { background: #e0e0e0; }",
        "#toc a.active { background: #cde; color: #036; font-weight: 600; }",
        "main { flex: 1; padding: 20px; min-width: 0; overflow-x: hidden; }",
        ".paper { margin-bottom: 2em; }",
        ".table-wrapper { overflow-x: auto; }",
        ".table { border-collapse: collapse; margin: 1em 0; }",
        ".table th, .table td { border: 1px solid #ddd; padding: 8px; }",
        ".metadata-table th { text-align: left; width: 120px; }",
        ".paper-sources { margin: 0.5em 0 1em; }",
        ".paper-sources summary { cursor: pointer; color: #555; font-size: 0.85em; }",
        ".low { background-color: #fdd; }",
        ".medium { background-color: #ffd; }",
        ".high { background-color: #dfd; }",
    ]


def build_html(metadata: dict, papers: dict[str, TablesFile]) -> str:
    html = ["<!DOCTYPE html>", "<html>", "<head>"]
    html.append("<meta charset='utf-8'>")
    html.append("<title>Paper2Table Viewer</title>")
    html.append("<style>")
    html.extend(build_css())
    html.append("</style>")
    html.append("</head><body>")

    html.extend(build_toc(papers))

    html.append("<main>")
    html.append("<h1>Paper2Table Viewer</h1>")
    if metadata:
        html.extend(build_metadata_html(metadata))

    uuid_to_reader: dict[str, str] = {
        s["uuid"]: s["reader"]
        for s in metadata.get("sources", [])
        if "uuid" in s and "reader" in s
    }

    html.append("<h2>Papers</h2>")
    for paper_i, (paper_name, content) in enumerate(papers.items()):
        paper_id = f"paper-{paper_i}"
        html.append(f"<div class='paper'><h3 id='{paper_id}'>{paper_name}</h3>")
        html.append(f"<p>Citation: {render_citation(content.citation)}</p>")
        paper_uuids = collect_paper_source_uuids(content)
        paper_sources = [
            s for s in metadata.get("sources", []) if s.get("uuid") in paper_uuids
        ]
        html.extend(build_paper_sources_html(paper_sources))
        for idx, table in enumerate(content.tables, 1):
            for fragment in table.get_table_fragments():
                frag_id = f"paper-{paper_i}-table-{idx}-page-{fragment.page}"
                html.extend(
                    build_fragment_html(idx, fragment, uuid_to_reader, anchor_id=frag_id)
                )
        html.append("</div>")

    html.append("</main>")
    html.append(f"<script>{_TOC_JS}</script>")
    html.append("</body></html>")
    return "\n".join(html)


def save_html(html: str, output_file: Path) -> None:
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate static HTML viewer for paper2tables results"
    )
    parser.add_argument(
        "input_dir", help="Directory with tables.metadata.json and *.tables.json"
    )
    parser.add_argument(
        "--out", default="viewer.html", help="Output HTML file (default: viewer.html)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    metadata, papers = load_papers_with_metadata(Path(args.input_dir))
    html = build_html(metadata, papers)
    save_html(html, Path(args.out))

    print(f"Viewer generated: {args.out}")
    webbrowser.open_new_tab(str(Path(args.out).absolute()))


if __name__ == "__main__":
    main()
