import json
from pathlib import Path

from tablevalidate.schema import TablesFile


def load_papers(directory: Path) -> dict[str, TablesFile]:
    papers = {}
    for paper_file in directory.glob("*.tables.json"):
        if paper_file.name == "tables.metadata.json":
            continue
        with open(paper_file, "r", encoding="utf-8") as f:
            papers[paper_file.name] = TablesFile.model_validate(json.load(f))
    return papers
