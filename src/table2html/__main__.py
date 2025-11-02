import argparse
import json
import webbrowser
from pathlib import Path

from utils.table_fragments import get_table_fragments


def load_papers(directory: Path):
    metadata_file = directory / "tables.metadata.json"
    metadata = {}
    if metadata_file.exists():
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

    papers = {}
    for paper_file in directory.glob("*.tables.json"):
        if paper_file.name == "tables.metadata.json":
            continue
        with open(paper_file, "r", encoding="utf-8") as f:
            papers[paper_file.name] = json.load(f)
    return metadata, papers


def build_html(metadata, papers):
    html = ["<!DOCTYPE html>", "<html>", "<head>"]
    html.append("<meta charset='utf-8'>")
    html.append("<title>Paper2Table Viewer</title>")
    html.append("<style>")
    html.append("body { font-family: Arial, sans-serif; margin: 20px; }")
    html.append(".paper { margin-bottom: 2em; }")
    html.append(".table { border-collapse: collapse; margin: 1em 0; width: 100%; }")
    html.append(".table th, .table td { border: 1px solid #ddd; padding: 8px; }")
    html.append(".low { background-color: #fdd; }")
    html.append(".medium { background-color: #ffd; }")
    html.append(".high { background-color: #dfd; }")
    html.append("</style>")
    html.append("</head><body>")

    html.append("<h1>Paper2Table Viewer</h1>")

    if metadata:
        html.append(
            "<h2>Metadata</h2><pre>{}</pre>".format(
                json.dumps(metadata, indent=2, ensure_ascii=False)
            )
        )

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
                    html.append("<tr class='{}'>".format(css_class))
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


def main():
    parser = argparse.ArgumentParser(
        description="Generate static HTML viewer for paper2tables results"
    )
    parser.add_argument(
        "input_dir", help="Directory with tables.metadata.json and *.tables.json"
    )
    parser.add_argument(
        "--out", default="viewer.html", help="Output HTML file (default: viewer.html)"
    )
    args = parser.parse_args()

    metadata, papers = load_papers(Path(args.input_dir))
    html = build_html(metadata, papers)
    save_html(html, Path(args.out))

    print(f"Viewer generated: {args.out}")
    webbrowser.open_new_tab(str(Path(args.out).absolute()))


if __name__ == "__main__":
    main()
