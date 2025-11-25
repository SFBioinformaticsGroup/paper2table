import logging
from typing import Optional

import pandas as pd
import pymupdf
import pymupdf.layout

from paper2table.mapping import TablesMapping
from paper2table.readers import document
from paper2table.tables_reader import TablesReader

_logger = logging.getLogger(__name__)


class PyMuPDFTable:
    table: pymupdf.table.Table

    def __init__(self, table: pymupdf.table.Table):
        self.table = table

    def to_dataframe(self, _column_names_hints: list[str]) -> pd.DataFrame:
        return self.table.to_pandas()


class PyMuPDFPage:
    def __init__(self, page: pymupdf.Page):
        self.page = page

    def extract_tables(self) -> list[PyMuPDFTable]:
        tables = self.page.find_tables().tables
        _logger.debug("Extracted %i tables", len(tables))
        return [PyMuPDFTable(table) for table in tables]

    @property
    def page_number(self) -> int:
        return self.page.number


class PyMuPDFDocument:
    document: pymupdf.Document
    _pages: list[PyMuPDFPage]

    def __init__(self, document: pymupdf.Document):
        self.document = document
        self._pages = [PyMuPDFPage(page) for page in document]

    @property
    def page_count(self) -> int:
        return self.document.page_count

    @property
    def pages(self) -> list[PyMuPDFPage]:
        return self._pages


def read_tables(
    pdf_path: str,
    column_names_hints: Optional[str] = None,
    mapping: Optional[TablesMapping] = None,
) -> TablesReader:

    with pymupdf.open(pdf_path) as pdf:
        return document.read_tables(
            pdf_path,
            column_names_hints=column_names_hints,
            mapping=mapping,
            open=lambda _: PyMuPDFDocument(pdf),
        )
