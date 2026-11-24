from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

from tablemerge.aliases import parse_column_aliases
from tablevalidate.schema import TablesFile
from utils.column_schema import ColumnSchema
from utils.column_values import NA_VALUES
from utils.jsonc import load_jsonc

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


def versioned_tool(name: str, package: str | None = None) -> str:
    version = get_package_version(package or name)
    return f"{name} {version}" if version else name


def parse_schema_columns(schema_content: str) -> list[tuple[str, str]]:
    return list(ColumnSchema.parse(schema_content).serialize().items())

def load_column_aliases(inline: str | None, path: str | None) -> dict[str, str]:
    if inline:
        return parse_column_aliases(inline)
    if path:
        return parse_column_aliases(Path(path).read_text(encoding="utf-8"))
    return {}


def add_reader_tool(
    reader: str,
    tools: list[str],
    seen_readers: set[str],
    seen_models: set[str],
) -> None:
    if reader.startswith("hybrid-"):
        reader = reader.removeprefix("hybrid-")

    head, _, tail = reader.partition("-")

    if head in READER_PACKAGES:
        if head not in seen_readers:
            seen_readers.add(head)
            tools.append(versioned_tool(head, READER_PACKAGES[head]))
        if tail and ":" in tail and tail not in seen_models:
            seen_models.add(tail)
            tools.append(tail)
        return

    if ":" in reader:
        if reader not in seen_models:
            seen_models.add(reader)
            tools.append(reader)
        return

    if reader not in seen_readers:
        seen_readers.add(reader)
        tools.append(reader)


def list_tools(tables_path: Path | None) -> list[str]:
    tools: list[str] = [versioned_tool("paper2table")]

    seen_readers: set[str] = set()
    seen_models: set[str] = set()

    if tables_path is not None:
        for metadata_path in sorted(tables_path.glob("*/tables.metadata.json")):
            metadata = load_jsonc(metadata_path)
            reader = metadata.get("reader")
            if reader:
                add_reader_tool(reader, tools, seen_readers, seen_models)

    tools.append(versioned_tool("spacy"))
    return tools


def read_tables_json_citation(path: Path) -> str:
    tablesfile = TablesFile.model_validate(load_jsonc(path))
    citation = tablesfile.citation
    if citation is None:
        return "[...]"
    if isinstance(citation, str):
        return citation
    return str(citation[0].value) if citation else "[...]"


def list_paper_citations(merges_path: Path | None) -> list[tuple[str, str]]:
    if merges_path is None:
        return []
    return sorted(
        (f.name.removesuffix(".tables.json"), read_tables_json_citation(f))
        for f in merges_path.glob("*.tables.json")
        if f.name != "tables.metadata.json"
    )


def files_section(
    merges_path: Path | None,
    tables_path: Path | None,
    gathers_path: Path | None,
) -> str:
    lines: list[str] = []
    if gathers_path is not None and (gathers_path / "csv").exists():
        lines.append("- `gathers/csv/`: output from `tablegather`, unmodified.")
    elif merges_path is not None and (merges_path / "csv").exists():
        lines.append("- `merges/csv/`: output from `tablemerge`, unmodified.")
    elif tables_path is not None and any(tables_path.glob("*/csv")):
        lines.append(
            "- `tables/<run-id>/csv/`: output from `paper2table`, unmodified."
        )
    lines.append("- `[path/to/curated.csv]`: same structure, with manual corrections.")
    return "\n".join(lines)


def generate_readme(
    merges_path: Path | None,
    tables_path: Path | None,
    gathers_path: Path | None,
    schema_content: str | None,
    aliases: dict[str, str],
) -> str:
    tools = list_tools(tables_path)
    tools_section = "\n".join(f"- {tool}" for tool in tools)

    papers = list_paper_citations(merges_path)
    if papers:
        papers_rows = "\n".join(f"| {title} | {doi} | [...] |" for title, doi in papers)
    else:
        papers_rows = "| [...] | [...] | [...] |"

    missing_values_line = ", ".join(sorted(NA_VALUES))

    files = files_section(merges_path, tables_path, gathers_path)

    columns = parse_schema_columns(schema_content) if schema_content else []

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
{files}

**Columns:**

| Column | Description | Type | Example | Alternative names | Hand-curated |
|---|---|---|---|---|---|
{columns_rows}

**Conventions:**
- Missing values: {missing_values_line}
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


def write_readme(
    output_path: Path,
    merges_path: Path | None,
    tables_path: Path | None,
    gathers_path: Path | None,
    schema_content: str | None,
    aliases: dict[str, str],
    override: bool,
) -> bool:
    if output_path.exists() and not override:
        return False
    output_path.write_text(
        generate_readme(
            merges_path, tables_path, gathers_path, schema_content, aliases
        ),
        encoding="utf-8",
    )
    return True
