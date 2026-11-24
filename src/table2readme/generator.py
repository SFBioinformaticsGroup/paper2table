from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

from tablemerge.aliases import parse_column_aliases
from tablevalidate.schema import TablesFile
from utils.column_schema import ColumnSchema
from utils.column_values import NA_VALUES
from utils.jsonc import load_jsonc
from utils.sample_values import collect_column_values, count_values
from utils.table_fragments import load_tablesfiles

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

TOP_VALUES_COUNT = 10


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


def citation_text(tablesfile: TablesFile) -> str:
    citation = tablesfile.citation
    if citation is None:
        return "[...]"
    if isinstance(citation, str):
        return citation
    return str(citation[0].value) if citation else "[...]"


def read_tables_json_citation(path: Path) -> str:
    return citation_text(TablesFile.model_validate(load_jsonc(path)))


def sorted_merges(papers: dict[str, TablesFile]) -> list[tuple[str, TablesFile]]:
    return sorted(
        (name.removesuffix(".tables.json"), tablesfile)
        for name, tablesfile in papers.items()
    )


def list_paper_citations(merges_path: Path | None) -> list[tuple[str, str]]:
    if merges_path is None:
        return []
    return [
        (name, citation_text(tablesfile))
        for name, tablesfile in sorted_merges(load_tablesfiles(merges_path))
    ]


def list_curators(papers: dict[str, TablesFile]) -> list[str]:
    curators: list[str] = []
    seen: set[str] = set()
    for tablesfile in papers.values():
        if not tablesfile.metadata or not tablesfile.metadata.curations:
            continue
        for curation in tablesfile.metadata.curations:
            if curation.curator and curation.curator not in seen:
                seen.add(curation.curator)
                curators.append(curation.curator)
    return curators


def count_corrections(papers: dict[str, TablesFile]) -> int:
    total = 0
    for tablesfile in papers.values():
        if tablesfile.metadata and tablesfile.metadata.curations:
            total += len(tablesfile.metadata.curations)
    return total


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


def top_values_subsection(
    papers: dict[str, TablesFile], schema: ColumnSchema
) -> str:
    if not papers:
        return ""
    values = collect_column_values(papers, schema)
    blocks: list[str] = []
    for column_name, column_values in values.items():
        top = count_values(column_values, TOP_VALUES_COUNT, None)
        blocks.append(f"**{column_name}:**")
        if not top:
            blocks.append("- (no values)")
        else:
            for value, occurrences in top:
                blocks.append(f"- {value} ({occurrences})")
        blocks.append("")
    return "\n".join(blocks).rstrip()


def top_values_section(
    merges: dict[str, TablesFile],
    gathers: dict[str, TablesFile],
    schema: ColumnSchema | None,
) -> str:
    if schema is None:
        return ""
    merges_block = top_values_subsection(merges, schema)
    gathers_block = top_values_subsection(gathers, schema)
    if not merges_block and not gathers_block:
        return ""
    parts = ["## Top values", ""]
    if merges_block:
        parts.extend(["### Merges", "", merges_block, ""])
    if gathers_block:
        parts.extend(["### Gathers", "", gathers_block, ""])
    return "\n".join(parts).rstrip() + "\n"


def generate_readme(
    merges_path: Path | None,
    tables_path: Path | None,
    gathers_path: Path | None,
    schema_content: str | None,
    aliases: dict[str, str],
) -> str:
    tools = list_tools(tables_path)
    tools_section = "\n".join(f"- {tool}" for tool in tools)

    merges = load_tablesfiles(merges_path) if merges_path else {}
    gathers = load_tablesfiles(gathers_path) if gathers_path else {}

    citations = [
        (name, citation_text(tablesfile))
        for name, tablesfile in sorted_merges(merges)
    ]
    if citations:
        papers_rows = "\n".join(
            f"| {title} | {doi} | [...] |" for title, doi in citations
        )
    else:
        papers_rows = "| [...] | [...] | [...] |"

    curators = list_curators(merges)
    members_line = ", ".join(curators) if curators else "[Name 1], [Name 2]"

    corrections = count_corrections(merges)
    corrections_line = str(corrections) if corrections > 0 else "[count]"

    missing_values_line = ", ".join(sorted(NA_VALUES))

    files = files_section(merges_path, tables_path, gathers_path)

    schema = ColumnSchema.parse(schema_content) if schema_content else None
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

    top_values = top_values_section(merges, gathers, schema)
    top_values_block = f"\n{top_values}" if top_values else ""

    return f"""\
# Project title

**Members:** {members_line}

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

- **Corrections made:** {corrections_line}
- **Types of errors found:** [e.g.: incorrectly extracted values, missing data]
- **Open issues:** [links or numbers]
{top_values_block}"""


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
