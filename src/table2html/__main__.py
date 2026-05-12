import argparse
import json
import webbrowser
from pathlib import Path

from utils.table_fragments import get_table_fragments, load_papers


def load_papers_with_metadata(directory: Path):
    metadata = {}
    metadata_file = directory / "tables.metadata.json"
    if metadata_file.exists():
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
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


def build_toc(papers) -> list:
    html = ['<nav id="toc">', '<div id="toc-inner">', "<b>Contents</b>", "<ul>"]
    for paper_i, (paper_name, content) in enumerate(papers.items()):
        paper_id = f"paper-{paper_i}"
        html.append(f'<li><a href="#{paper_id}">{paper_name}</a>')
        fragments = [
            (idx, fragment)
            for idx, table in enumerate(content.get("tables", []), 1)
            for fragment in get_table_fragments(table)
        ]
        if fragments:
            html.append("<ul>")
            for idx, fragment in fragments:
                page = fragment.get("page", "?")
                frag_id = f"paper-{paper_i}-table-{idx}-page-{page}"
                html.append(
                    f'<li><a href="#{frag_id}">Table {idx}, p.&nbsp;{page}</a></li>'
                )
            html.append("</ul>")
        html.append("</li>")
    html.extend(["</ul>", "</div>", "</nav>"])
    return html


def build_metadata_html(metadata) -> list:
    html = ["<h2>Metadata</h2>"]
    scalar_fields = {k: v for k, v in metadata.items() if k != "sources"}
    if scalar_fields:
        html.append("<table class='table metadata-table'>")
        for key, value in scalar_fields.items():
            html.append(f"<tr><th>{key}</th><td>{value}</td></tr>")
        html.append("</table>")
    sources = metadata.get("sources")
    if sources:
        html.append("<h3>Sources</h3>")
        all_keys = {k for s in sources for k in s}
        preferred = ["uuid", "reader", "path"]
        source_keys = [k for k in preferred if k in all_keys] + sorted(
            all_keys - set(preferred)
        )
        html.append("<table class='table'>")
        html.append("<tr>" + "".join(f"<th>{k}</th>" for k in source_keys) + "</tr>")
        for source in sources:
            html.append(
                "<tr>"
                + "".join(f"<td>{_source_cell(source, k)}</td>" for k in source_keys)
                + "</tr>"
            )
        html.append("</table>")
    return html


_META_KEYS = {"agreement_level_", "sources_"}


def is_empty_row(row):
    return all(not row.get(k) for k in row if k not in _META_KEYS)


def agreement_css_class(level: int) -> str:
    if level <= 1:
        return "low"
    if level == 2:
        return "medium"
    return "high"


def build_data_row(row: dict, columns: list, uuid_to_reader=None) -> list:
    css_class = agreement_css_class(row.get("agreement_level_", 0))
    html = [f"<tr class='{css_class}'>"]
    for col in columns:
        if col == "readers_":
            source_ids = row.get("sources_") or []
            mapping = uuid_to_reader or {}
            readers = list(
                dict.fromkeys(mapping[sid] for sid in source_ids if sid in mapping)
            )
            val = ", ".join(readers)
        else:
            val = row.get(col, "")
            if isinstance(val, list):
                val = ", ".join(str(v) for v in val)
        html.append(f"<td>{val}</td>")
    html.append("</tr>")
    return html


def build_fragment_html(idx, fragment, uuid_to_reader=None, anchor_id=None) -> list:
    page = fragment.get("page", "?")
    id_attr = f' id="{anchor_id}"' if anchor_id else ""
    html = [f"<h4{id_attr}>Table {idx}, page {page}</h4>"]
    all_rows = fragment.get("rows", [])
    rows = [r for r in all_rows if not is_empty_row(r)]
    skipped = len(all_rows) - len(rows)
    if not rows:
        html.append("<p><i>No rows</i></p>")
        if skipped:
            html.append(f"<p><i>({skipped} empty rows not shown)</i></p>")
        return html
    has_sources = "sources_" in rows[0]
    columns = [k for k in rows[0].keys() if k != "sources_"]
    if has_sources:
        columns.append("readers_")
        columns.append("sources_")
    html.append("<table class='table'>")
    html.append("<tr>" + "".join(f"<th>{col}</th>" for col in columns) + "</tr>")
    for row in rows:
        html.extend(build_data_row(row, columns, uuid_to_reader))
    html.append("</table>")
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


def build_css() -> list:
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
        "main { flex: 1; padding: 20px; min-width: 0; }",
        ".paper { margin-bottom: 2em; }",
        ".table { border-collapse: collapse; margin: 1em 0; width: 100%; }",
        ".table th, .table td { border: 1px solid #ddd; padding: 8px; }",
        ".metadata-table th { text-align: left; width: 120px; }",
        ".low { background-color: #fdd; }",
        ".medium { background-color: #ffd; }",
        ".high { background-color: #dfd; }",
    ]


def build_html(metadata, papers):
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

    uuid_to_reader = {
        s["uuid"]: s["reader"]
        for s in metadata.get("sources", [])
        if "uuid" in s and "reader" in s
    }

    html.append("<h2>Papers</h2>")
    for paper_i, (paper_name, content) in enumerate(papers.items()):
        paper_id = f"paper-{paper_i}"
        html.append(f"<div class='paper'><h3 id='{paper_id}'>{paper_name}</h3>")
        html.append(f"<p>Citation: {content.get('citation','')}</p>")
        for idx, table in enumerate(content.get("tables", []), 1):
            for fragment in get_table_fragments(table):
                page = fragment.get("page", "?")
                frag_id = f"paper-{paper_i}-table-{idx}-page-{page}"
                html.extend(
                    build_fragment_html(
                        idx, fragment, uuid_to_reader, anchor_id=frag_id
                    )
                )
        html.append("</div>")

    html.append("</main>")
    html.append(f"<script>{_TOC_JS}</script>")
    html.append("</body></html>")
    return "\n".join(html)


def save_html(html, output_file: Path):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)


def parse_args():
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
