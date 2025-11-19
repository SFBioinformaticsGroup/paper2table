from pathlib import Path
from typing import Any

from pydantic import create_model
from pydantic_ai import Agent, BinaryContent

from utils.columns_schema import parse_schema

from . import pdfplumber
from .pdfplumber import TablesSchema

from ..tables_reader import TablesReader


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


def read_tables(path: str, model: str, schema: str) -> TablesReader:
    paper_path = Path(path)
    agent = Agent(
        model,
        output_type=TablesSchema,
        instructions=build_instructions(schema),
    )
    output = agent.run_sync(
        [
            BinaryContent(data=paper_path.read_bytes(), media_type="application/pdf"),
        ]
    ).output
    print(output.model_dump_json())
    return pdfplumber.read_tables(path, schema=output)
