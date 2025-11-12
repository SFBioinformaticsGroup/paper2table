from pathlib import Path
from typing import Any

from pydantic import create_model
from pydantic_ai import Agent, BinaryContent

from utils.columns_schema import parse_schema

from . import pdfplumber
from .pdfplumber import TablesSchema

from ..tables_reader import TablesReader
from ..tables_reader.pydantic import TablesModelWrapper


def build_instructions(schema):
    return (
        "CONTEXT",
        "=======",
        "You are a PhD researcher.",
        "",
        "TASK",
        "====",
        "You are going to read the given paper and determine where ",
        "there are tables that correspond to the given COLUMN STRUCTURE",
        "",
        "COLUMN STRUCTURE",
        "==================",
        "You are only going to look for tables that (approximately) ",
        "have the following this structure:",
        "",
        ", ".join(parse_schema(schema).keys()),
        "",
        "EXPECTED OUTPUT",
        "===============",
        "When you find a table extract the following information:",
        " * title: try to find its title or caption.",
        "   If there is none, generate a short but descriptive title for it.",
        " * first_page and last_page: annotate the consecutive range of pages (1-based)",
        "   where it starts and where it ends.",
        " * header_mode: determine if the tables has headers in all its pages (all_pages), just the first page (first_page_only)",
        "   or it has no headers at all (none)",
        " * column_mappings: determine which column number (0-based) best matches which column from COLUMN STRUCTURE",
        "",
        "RESTRICTIONS",
        "============",
        " * When looking for tables, only consider data that is in tabular format.",
        "   Ignore any plain text paragraph",
        " * If there is no data available for a column in COLUMN STRUCTURE, just ignore it",
        " * When possible, you'll generate a citation output field with an APA-style cite of the paper from where the tables were extracted",
    )


def read_tables(path: str, model: str, schema: str) -> TablesReader:
    print("\n".join(build_instructions(schema)))
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
