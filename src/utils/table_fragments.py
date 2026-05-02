import json
from pathlib import Path


def get_table_fragments(table: dict) -> list[dict]:
    return table["table_fragments"] if "table_fragments" in table else [table]


def load_papers(directory: Path) -> dict:
    papers = {}
    for paper_file in directory.glob("*.tables.json"):
        if paper_file.name == "tables.metadata.json":
            continue
        with open(paper_file, "r", encoding="utf-8") as f:
            papers[paper_file.name] = json.load(f)
    return papers
