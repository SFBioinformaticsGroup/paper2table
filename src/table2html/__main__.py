import argparse
import json
import webbrowser
from pathlib import Path

from utils.table_fragments import get_table_fragments, load_papers


def load_papers_with_metadata(directory: Path):
    metadata = {}
    for candidate in ("tablemerge.metadata.json", "tables.metadata.json"):
        metadata_file = directory / candidate
        if metadata_file.exists():
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            break
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


def build_html(metadata, papers):
    html = ["<!DOCTYPE html>", "<html>", "<head>"]
    html.append("<meta charset='utf-8'>")
    html.append("<title>Paper2Table Viewer</title>")
    html.append("<style>")
    html.append("body { font-family: Arial, sans-serif; margin: 20px; }")
    html.append(".paper { margin-bottom: 2em; }")
    html.append(".table { border-collapse: collapse; margin: 1em 0; width: 100%; }")
    html.append(".table th, .table td { border: 1px solid #ddd; padding: 8px; }")
    html.append(".metadata-table th { text-align: left; width: 120px; }")
    html.append(".low { background-color: #fdd; }")
    html.append(".medium { background-color: #ffd; }")
    html.append(".high { background-color: #dfd; }")
    html.append("</style>")
    html.append("</head><body>")

    html.append("<h1>Paper2Table Viewer</h1>")

    if metadata:
        html.append("<h2>Metadata</h2>")
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
            source_keys = [k for k in preferred if k in all_keys] + sorted(all_keys - set(preferred))
            html.append("<table class='table'>")
            html.append("<tr>" + "".join(f"<th>{k}</th>" for k in source_keys) + "</tr>")
            for source in sources:
                html.append("<tr>" + "".join(f"<td>{_source_cell(source, k)}</td>" for k in source_keys) + "</tr>")
            html.append("</table>")

    html.append("<h2>Papers</h2>")
    for paper_name, content in papers.items():
        html.append(f"<div class='paper'><h3>{paper_name}</h3>")
        html.append(f"<p>Citation: {content.get('citation','')}</p>")

        for idx, table in enumerate(content.get("tables", []), 1):
            fragments = get_table_fragments(table)
            for fragment in fragments:
                html.append(f"<h4>Table {idx}, page {fragment.get('page','?')}</h4>")
                rows = fragment.get("rows", [])
                if not rows:
                    html.append("<p><i>No rows</i></p>")
                    continue

                # Build header from keys
                columns = list(rows[0].keys())
                html.append("<table class='table'>")
                html.append(
                    "<tr>" + "".join(f"<th>{col}</th>" for col in columns) + "</tr>"
                )

                for row in rows:
                    row_agreement_level = row.get("agreement_level_", 0)
                    css_class = (
                        "low"
                        if row_agreement_level <= 1
                        else "medium" if row_agreement_level == 2 else "high"
                    )
                    html.append(f"<tr class='{css_class}'>")
                    for col in columns:
                        html.append(f"<td>{row.get(col,'')}</td>")
                    html.append("</tr>")

                html.append("</table>")

        html.append("</div>")

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
