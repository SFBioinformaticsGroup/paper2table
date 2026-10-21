import json
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

from tablevalidate.schema import TablesFile

from .pipeline import Pipeline

READER_PACKAGES = {
    "pdfplumber": "pdfplumber",
    "pymupdf": "pymupdf",
    "camelot": "camelot-py",
    "img2table": "img2table",
}

TYPE_MAP = {
    "str": "text",
    "scientific_name": "text",
    "int": "number",
    "float": "number",
}


def get_package_version(package: str) -> str:
    try:
        return pkg_version(package)
    except PackageNotFoundError:
        return ""


def parse_schema_columns(schema_path: str) -> list[tuple[str, str]]:
    columns = []
    for line in Path(schema_path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" in line:
            name, type_ = line.split(":", 1)
            columns.append((name.strip(), type_.strip()))
        else:
            columns.append((line, ""))
    return columns


def list_tools(pipeline: Pipeline) -> list[str]:
    tools = []
    version = get_package_version("paper2table")
    tools.append(f"paper2table {version}" if version else "paper2table")

    if pipeline.extract:
        seen_models: set[str] = set()
        seen_readers: set[str] = set()
        for run in pipeline.extract.runs:
            if run.reader in ("agent", "hybrid") and run.model and run.model not in seen_models:
                tools.append(run.model)
                seen_models.add(run.model)
            if run.reader in READER_PACKAGES and run.reader not in seen_readers:
                reader_pkg = READER_PACKAGES[run.reader]
                reader_version = get_package_version(reader_pkg)
                tools.append(f"{run.reader} {reader_version}" if reader_version else run.reader)
                seen_readers.add(run.reader)

    if pipeline.merge and (
        pipeline.merge.column_name_semantic_alignment
        or pipeline.merge.column_value_semantic_alignment
    ):
        spacy_version = get_package_version("spacy")
        tools.append(f"spacy {spacy_version}" if spacy_version else "spacy")

    return tools


def parse_aliases(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if line and ":" in line:
            original, renamed = line.split(":", 1)
            result[original.strip()] = renamed.strip()
    return result


def load_column_aliases(pipeline: Pipeline) -> dict[str, str]:
    if pipeline.merge:
        if pipeline.merge.column_aliases:
            return parse_aliases(pipeline.merge.column_aliases)
        aliases_path = pipeline.merge.column_aliases_path or None
        if aliases_path:
            p = Path(aliases_path)
            if p.exists():
                return parse_aliases(p.read_text(encoding="utf-8"))

    aliases_file = Path(pipeline.working_path) / "column_aliases.txt"
    if aliases_file.exists() and aliases_file.read_text(encoding="utf-8").strip():
        return parse_aliases(aliases_file.read_text(encoding="utf-8"))

    return {}


def read_tables_json_citation(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    citation = data.get("citation")
    if isinstance(citation, str):
        return citation
    if isinstance(citation, list) and citation:
        first = citation[0]
        if isinstance(first, dict):
            return str(first.get("value", "[...]"))
        return str(first)
    return "[...]"


def list_paper_citations(working_path: str) -> list[tuple[str, str]]:
    merges_dir = Path(working_path) / "merges"
    if merges_dir.exists():
        entries = sorted(
            (f.name.removesuffix(".tables.json"), read_tables_json_citation(f))
            for f in merges_dir.glob("*.tables.json")
            if f.name != "tables.metadata.json"
        )
        if entries:
            return entries

    papers_dir = Path(working_path) / "papers"
    if papers_dir.exists():
        return sorted((f.stem, "[...]") for f in papers_dir.glob("*.pdf"))

    return []


def generate_readme(pipeline: Pipeline, schema_path: str | None) -> str:
    tools = list_tools(pipeline)
    tools_section = "\n".join(f"- {tool}" for tool in tools)

    papers = list_paper_citations(pipeline.working_path)
    if papers:
        papers_rows = "\n".join(f"| {title} | {doi} | [...] |" for title, doi in papers)
    else:
        papers_rows = "| [...] | [...] | [...] |"

    files_lines = []
    if pipeline.gather and "csv" in pipeline.gather.export:
        files_lines.append("- `gathers/csv/`: output from `tablegather`, unmodified.")
    elif pipeline.merge and "csv" in pipeline.merge.export:
        files_lines.append("- `merges/csv/`: output from `tablemerge`, unmodified.")
    elif pipeline.extract and "csv" in pipeline.extract.export:
        files_lines.append("- `tables/<run-id>/csv/`: output from `paper2table`, unmodified.")
    files_lines.append("- `[path/to/curated.csv]`: same structure, with manual corrections.")
    files_section = "\n".join(files_lines)

    if schema_path:
        columns = parse_schema_columns(schema_path)
    else:
        columns = []

    aliases = load_column_aliases(pipeline)
    reverse_aliases: dict[str, list[str]] = {}
    for original, renamed in aliases.items():
        reverse_aliases.setdefault(renamed, []).append(original)

    if columns:
        columns_rows = "\n".join(
            f"| {name} | [...] | {TYPE_MAP.get(type_, type_) if type_ else 'text'} | [...] | {', '.join(reverse_aliases.get(name, []))} | [...] |"
            for name, type_ in columns
        )
    else:
        columns_rows = "| [...] | [...] | [...] | [...] | | [...] |"

    return f"""\
# Project title

**Members:** [Name 1], [Name 2]

**Topic:** [project topic]

## Goal and question

*Write this before running the pipeline.*

- **Question:** [What...?]
- **Goal:** Using the table extracted from the papers, we want to [...].
- **Information needed from the papers:** [...]

## Papers used

| Title | DOI or link | License |
|---|---|---|
{papers_rows}

## Tools and version

{tools_section}

## Data model

**What each row represents:** [e.g.: a data point from a paper / a site / a study]

**Files:**
{files_section}

**Columns:**

| Column | Description | Type | Example | Alternative names | Hand-curated |
|---|---|---|---|---|---|
{columns_rows}

**Conventions:**
- Missing values: [how they are marked, e.g.: empty cell]
- Units: [...]
- Date format: [...]
- Allowed values: [if any column has a fixed set]

**Changes between raw and curated:** [no columns added or removed / column X was added]

## Results

What table was obtained and what it shows. Mention the result files.

## Curation

- **Corrections made:** [count]
- **Types of errors found:** [e.g.: incorrectly extracted values, missing data]
- **Open issues:** [links or numbers]
"""


def write_readme(pipeline: Pipeline, schema_path: str | None, override: bool = False) -> None:
    readme_path = Path(pipeline.working_path) / "README.md"
    if readme_path.exists() and not override:
        return
    readme_path.write_text(generate_readme(pipeline, schema_path), encoding="utf-8")
