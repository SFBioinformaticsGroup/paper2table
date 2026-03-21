import logging
from pathlib import Path
from typing import Callable

from pydantic_ai import Agent, BinaryContent

from utils.columns_schema import parse_schema

from ..mapping import TablesMapping
from ..tables_reader import TablesReader

_logger = logging.getLogger(__name__)


def build_instructions(schema):
    return (
        "CONTEXT",
        "=======",
        "You are a PhD researcher analyzing scientific papers.",
        "",
        "TASK",
        "====",
        "Your goal is to read the provided PDF document and identify all tables that correspond "
        "approximately to a specific COLUMN STRUCTURE. Once identified, you will extract metadata "
        "and mapping information about each relevant table.",
        "",
        "COLUMN STRUCTURE",
        "==================",
        "You must look for tables that approximately match the following columns:",
        "",
        ", ".join(parse_schema(schema).keys()),
        "",
        "EXPECTED OUTPUT",
        "===============",
        "For each relevant table you find, extract and report the following information:",
        "",
        " * title: The title or caption of the table. If no title is present, generate a short, descriptive one.",
        " * first_page and last_page: annotate the consecutive range of pages (1-based) where it starts and where it ends.",
        " * header_mode: Specify one of the following values:",
        "   * all_pages: The table includes headers on every page.",
        "   * first_page_only: The table includes headers only on the first page.",
        "   * none: The table has no headers.",
        " * column_mappings: determine which column number (0-based) best matches which column from COLUMN STRUCTURE",
        " * citation: When possible, include the paper's citation in APA format from which the table was extracted.",
        "",
        "RESTRICTIONS",
        "============",
        " * Only consider data that appears in tabular form. Ignore paragraphs or narrative text.",
        " * If a specific column from the COLUMN STRUCTURE is missing in the table, omit it from the output.",
        " * Focus only on tables relevant to the specified COLUMN STRUCTURE.",
        " * Ensure that extracted data and metadata are accurate and consistent with the source document.",
    )


def read_tables(
    path: str,
    model: str,
    schema: str,
    mappings_path: Path,
    reader: Callable[[str, TablesMapping], TablesReader],
) -> TablesReader:
    paper_path = Path(path)
    mapping_path = mappings_path / paper_path.name.replace(".pdf", ".mapping.json")
    if mapping_path.exists():
        _logger.debug("Using existing mapping for %s", paper_path)
        mapping = TablesMapping.model_validate_json(mapping_path.read_text())
    else:
        _logger.debug(
            "Mapping for %s doesn't exist. Generating it with model", paper_path
        )
        agent = Agent(
            model,
            output_type=TablesMapping,
            instructions=build_instructions(schema),
        )
        mapping = agent.run_sync(
            [
                BinaryContent(
                    data=paper_path.read_bytes(), media_type="application/pdf"
                ),
            ]
        ).output
        mappings_path.mkdir(parents=True, exist_ok=True)
        mapping_path.write_text(mapping.model_dump_json())
    return reader(path, mapping)
