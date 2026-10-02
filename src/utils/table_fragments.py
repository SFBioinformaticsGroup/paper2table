from pathlib import Path

from tablevalidate.schema import TablesFile

from .jsonc import load_jsonc


def load_papers(directory: Path) -> dict[str, TablesFile]:
    papers = {}
    for paper_file in directory.glob("*.tables.json"):
        if paper_file.name == "tables.metadata.json":
            continue
        papers[paper_file.name] = TablesFile.model_validate(load_jsonc(paper_file))
    return papers
