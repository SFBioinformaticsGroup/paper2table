import json
import logging
import os
import sys

from pandas import DataFrame
import camelot
from PyPDF2 import PdfReader

_logger = logging.getLogger(__name__)


class Table:
    """Single table extracted from a PDF."""

    def __init__(self, index: int, page_number: int, dataframe: DataFrame):
        self.index = index
        self.page_number = page_number
        self.df = dataframe

    def to_dict(self):
        """Return structured representation with rows + metadata."""
        return {
            "rows": self.df.to_dict(orient="records"),
            "metadata": {
                "page": self.page_number,
                "index": self.index,
            },
        }


class Tables:
    """Wrapper class for extracted tables and document metadata."""

    def __init__(self, pdf_path: str, tables: list[Table], citation=None):
        self.pdf_path = pdf_path
        self.filename = os.path.basename(pdf_path)
        self.tables = tables
        self.citation = citation

    def to_dict(self):
        return {
            "tables": [table.to_dict() for table in self.tables],
            "citation": self.citation,
            "metadata": {
                "filename": self.filename,
            },
        }


def extract_metadata(pdf_path: str):
    """Extract PDF metadata and attempt to format in APA citation style."""
    try:
        reader = PdfReader(pdf_path)
        info = reader.metadata
    except Exception:
        return None

    author = info.get("/Author", "Unknown Author")
    title = info.get("/Title", "Untitled")
    year = "n.d."

    if "/CreationDate" in info:
        date_str = info["/CreationDate"]
        if date_str.startswith("D:"):
            year = date_str[2:6]

    citation = f"{author}. ({year}). {title}. [PDF file]."
    return citation


def read_tables(pdf_path: str) -> dict:
    try:
        camelot_tables = camelot.read_pdf(
            pdf_path, suppress_stdout=True, flavor="hybrid", pages="all"
        )
    except Exception as e:
        _logger.warning(f"Error reading {pdf_path}: {e}")
        return Tables(pdf_path, []).to_dict()

    tables = []
    for idx, table in enumerate(camelot_tables):
        page_number = table.page
        dataframe = table.df
        tables.append(Table(idx, page_number, dataframe))

    citation = extract_metadata(pdf_path)
    return Tables(pdf_path, tables, citation).to_dict()
